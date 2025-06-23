"""
실거래가 조회/분석 도구

예시 사용법:

from mcp_kr_realestate.tools.transaction_tools import parse_nrg_trade_xml, summarize_nrg_trade

df = parse_nrg_trade_xml('mcp_kr_realestate/utils/data/NRG_11680_202506.xml')
summary = summarize_nrg_trade(df)
print(summary)
"""

import logging
from typing import Any, Optional
from mcp_kr_realestate.server import mcp, ctx
from mcp.types import TextContent
from mcp_kr_realestate.utils.ctx_helper import with_context
from mcp_kr_realestate.registry.initialize_registry import initialize_registry
import pandas as pd
import xml.etree.ElementTree as ET
from pathlib import Path
import os
from dotenv import load_dotenv
import json
import requests
import subprocess
import shutil
import numpy as np
from mcp_kr_realestate.apis.officetel_trade import get_officetel_trade_data
from mcp_kr_realestate.apis.rh_trade import get_rh_trade_data
from mcp_kr_realestate.apis.indutrade import get_indu_trade_data
from mcp_kr_realestate.apis.land_trade import get_land_trade_data
from mcp_kr_realestate.apis.apt_rent import get_apt_rent_data
from mcp_kr_realestate.apis.apt_trade import get_apt_trade_data as api_get_apt_trade_data
from mcp_kr_realestate.apis.officetel_rent import get_officetel_rent_data
from mcp_kr_realestate.apis.rh_rent import get_rh_rent_data
from mcp_kr_realestate.apis.sh_rent import get_sh_rent_data
from mcp_kr_realestate.apis.sh_trade import get_sh_trade_data

logger = logging.getLogger("mcp-kr-realestate")
tool_registry = initialize_registry()
load_dotenv()

# 로그 파일 설정 (중복 핸들러 방지)
log_dir = os.path.join(os.path.dirname(__file__), '../utils/logs')
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, 'realestate_tool.log')
file_logger = logging.getLogger("realestate_tool")
if not file_logger.handlers:
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    file_logger.addHandler(handler)
    file_logger.setLevel(logging.DEBUG)

@mcp.tool(
    name="get_region_codes",
    description="""
입력한 지역명(region_name, 예: '성북구', '강남구', '역삼동' 등)으로 법정동 코드(5자리, lawd_cd) 목록을 조회합니다. 
시도/시군구/읍면동명 등 다양한 지역명 일부만 입력해도 부분 일치로 검색됩니다.

Arguments:
- region_name (str, required): 조회할 지역명(구/동/시 등, 일부만 입력해도 됨)

Returns: 해당 지역명이 포함된 법정동 코드 목록(JSON)
""",
    tags={"법정동코드", "지역코드", "검색"}
)
def get_region_codes(region_name: str, ctx: Optional[Any] = None) -> TextContent:
    """
    입력한 지역명(region_name)으로 법정동 코드 목록을 반환합니다.
    Args:
        region_name (str): 구/동/시 등 일부명
    Returns:
        TextContent: JSON 리스트(법정동코드, 시도명, 시군구명, 읍면동명 등)
    """
    from mcp_kr_realestate.utils.region_codes import get_region_code_df
    import json
    def call(context):
        try:
            df = get_region_code_df()
            # 부분 일치(대소문자 무시)
            mask = (
                df['시도명'].str.contains(region_name, case=False, na=False) |
                df['시군구명'].str.contains(region_name, case=False, na=False) |
                df['읍면동명'].str.contains(region_name, case=False, na=False)
            )
            filtered = df[mask].copy()
            if filtered.empty:
                return json.dumps({"error": f"'{region_name}'(으)로 일치하는 법정동 코드가 없습니다."}, ensure_ascii=False)
            # 주요 컬럼만 반환
            result = filtered[['법정동코드', '시도명', '시군구명', '읍면동명']].to_dict(orient='records')
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": f"법정동 코드 조회 중 오류: {e}"}, ensure_ascii=False)
    result = with_context(ctx, "get_region_codes", call)
    return TextContent(type="text", text=result)

@mcp.tool(
    name="get_commercial_property_trade_data",
    description="""
상업업무용(사무실, 상가 등) 부동산 매매 실거래가 데이터를 조회합니다.
이 도구를 사용하기 전에 반드시 먼저 법정동 코드(5자리, lawd_cd)를 조회하고 선택해야 합니다. 법정동 코드는 실거래가 데이터를 조회하는 데 필수입니다.

사용 절차 안내:
1. 먼저 'get_region_codes' 도구를 사용하여 원하는 지역의 법정동 코드(lawd_cd)를 조회하세요.
2. 조회한 lawd_cd(5자리)와 거래년월(deal_ymd, 6자리: YYYYMM)을 본 도구에 입력하여 실거래가 XML 데이터를 조회하세요.

동별(byDong)로 이미 거래+통계가 묶여 반환되므로, 별도의 동 필터링 도구 없이 원하는 동의 거래/통계를 바로 추출할 수 있습니다.

Arguments:
- lawd_cd (str, required): 법정동코드(5자리)
- deal_ymd (str, required): 거래년월(YYYYMM, 6자리)

Returns: 실거래가 XML 데이터가 저장된 파일 경로를 반환합니다.
""",
    tags={"실거래가", "상업업무용", "상가", "사무실"}
)
def get_commercial_property_trade_data(lawd_cd: str, deal_ymd: str, ctx: Optional[Any] = None) -> TextContent:
    """
    상업업무용 부동산 매매 실거래가 API 호출 및 전체 데이터 JSON+통계 반환 (curl subprocess + requests fallback, 반복 수집)
    Args:
        lawd_cd (str): 법정동코드 5자리
        deal_ymd (str): 거래년월 (YYYYMM)
    Returns:
        TextContent: 전체 거래 데이터와 통계가 포함된 JSON 문자열
    """
    def call(context):
        return context.nrg_trade.get_trade_data(lawd_cd=lawd_cd, deal_ymd=deal_ymd)
        
    result = with_context(ctx, "get_commercial_property_trade_data", call)
    return TextContent(type="text", text=result)

@mcp.tool(
    name="get_land_trade_data",
    description="""
이 도구를 사용하기 전에 반드시 먼저 법정동 코드(5자리, lawd_cd)를 조회하고 선택해야 합니다. 법정동 코드는 토지 실거래가 데이터를 조회하는 데 필수입니다.

사용 절차 안내:
1. 먼저 'get_region_codes' 도구를 사용하여 원하는 지역의 법정동 코드(lawd_cd)를 조회하세요.
2. 조회한 lawd_cd(5자리)와 거래년월(deal_ymd, 6자리: YYYYMM)을 본 도구에 입력하여 토지 매매 실거래가 데이터를 조회하세요.

동별(byDong)로 이미 거래+통계가 묶여 반환되므로, 별도의 동 필터링 도구 없이 원하는 동의 거래/통계를 바로 추출할 수 있습니다.

Arguments:
- lawd_cd (str, required): 법정동코드(5자리)
- deal_ymd (str, required): 거래년월(YYYYMM, 6자리)

Returns: 토지 매매 실거래가 전체 거래+통계(byDong) JSON
""",
    tags={"토지", "실거래가", "매매"}
)
def mcp_get_land_trade_data(lawd_cd: str, deal_ymd: str, ctx: Optional[Any] = None) -> TextContent:
    """
    토지 매매 실거래가 데이터를 동별(byDong) 통계+거래 리스트로 반환
    """
    result = get_land_trade_data(lawd_cd, deal_ymd)
    return TextContent(type="text", text=result)

@mcp.tool(
    name="get_industrial_property_trade_data",
    description="""
산업용(공장, 창고 등) 부동산 매매 실거래가 데이터를 조회합니다.
이 도구를 사용하기 전에 반드시 먼저 법정동 코드(5자리, lawd_cd)를 조회하고 선택해야 합니다. 법정동 코드는 실거래가 데이터를 조회하는 데 필수입니다.

사용 절차 안내:
1. 먼저 'get_region_codes' 도구를 사용하여 원하는 지역의 법정동 코드(lawd_cd)를 조회하세요.
2. 조회한 lawd_cd(5자리)와 거래년월(deal_ymd, 6자리: YYYYMM)을 본 도구에 입력하여 공장 및 창고 등 부동산 매매 실거래가 데이터를 조회하세요.

동별(byDong)로 이미 거래+통계가 묶여 반환되므로, 별도의 동 필터링 도구 없이 원하는 동의 거래/통계를 바로 추출할 수 있습니다.

Arguments:
- lawd_cd (str, required): 법정동코드(5자리)
- deal_ymd (str, required): 거래년월(YYYYMM, 6자리)

Returns: 공장 및 창고 등 부동산 매매 실거래가 전체 거래+통계(byDong) JSON
""",
    tags={"공장창고", "산업용", "industrial", "실거래가", "매매"}
)
def get_industrial_property_trade_data(lawd_cd: str, deal_ymd: str, ctx: Optional[Any] = None) -> TextContent:
    """
    공장/창고 등 산업용 부동산 매매 실거래가 API 호출 및 전체 데이터 JSON+통계 반환
    """
    def call(context):
        return get_indu_trade_data(lawd_cd=lawd_cd, deal_ymd=deal_ymd)
    result = with_context(ctx, "get_industrial_property_trade_data", call)
    return TextContent(type="text", text=result)

@mcp.tool(
    name="get_apt_trade_data",
    description="""
이 도구를 사용하기 전에 반드시 먼저 법정동 코드(5자리, lawd_cd)를 조회하고 선택해야 합니다. 법정동 코드는 아파트 실거래가 데이터를 조회하는 데 필수입니다.

사용 절차 안내:
1. 먼저 'get_region_codes' 도구를 사용하여 원하는 지역의 법정동 코드(lawd_cd)를 조회하세요.
2. 조회한 lawd_cd(5자리)와 거래년월(deal_ymd, 6자리: YYYYMM)을 본 도구에 입력하여 아파트 매매 실거래가 데이터를 조회하세요.

동별(byDong)로 이미 거래+통계가 묶여 반환되므로, 별도의 동 필터링 도구 없이 원하는 동의 거래/통계를 바로 추출할 수 있습니다.

Arguments:
- lawd_cd (str, required): 법정동코드(5자리)
- deal_ymd (str, required): 거래년월(YYYYMM, 6자리)

Returns: 아파트 매매 실거래가 전체 거래+통계(byDong) JSON
""",
    tags={"아파트", "실거래가", "매매"}
)
def get_apt_trade_data(lawd_cd: str, deal_ymd: str, ctx: Optional[Any] = None) -> TextContent:
    """
    아파트 매매 실거래가 API 호출 및 XML 저장
    Args:
        lawd_cd (str): 법정동코드 5자리
        deal_ymd (str): 거래년월 (YYYYMM)
    Returns:
        TextContent: 저장된 XML 파일 경로
    """
    def call(context):
        return api_get_apt_trade_data(lawd_cd, deal_ymd)
    result = with_context(ctx, "get_apt_trade_data", call)
    return TextContent(type="text", text=result)

@mcp.tool(
    name="get_apt_rent_data",
    description="""
이 도구를 사용하기 전에 반드시 먼저 법정동 코드(5자리, lawd_cd)를 조회하고 선택해야 합니다. 법정동 코드는 아파트 전월세 실거래가 데이터를 조회하는 데 필수입니다.

사용 절차 안내:
1. 먼저 'get_region_codes' 도구를 사용하여 원하는 지역의 법정동 코드(lawd_cd)를 조회하세요.
2. 조회한 lawd_cd(5자리)와 거래년월(deal_ymd, 6자리: YYYYMM)을 본 도구에 입력하여 아파트 전월세 실거래가 데이터를 조회하세요.

동별(byDong)로 전세/월세를 구분하여 거래+통계가 묶여 반환되므로, 별도의 동 필터링 도구 없이 원하는 동의 거래/통계를 바로 추출할 수 있습니다.

Arguments:
- lawd_cd (str, required): 법정동코드(5자리)
- deal_ymd (str, required): 거래년월(YYYYMM, 6자리)

Returns: 아파트 전월세 실거래가 전체 거래+통계(byDong, 전세/월세 구분) JSON
""",
    tags={"아파트", "전월세", "실거래가"}
)
def mcp_get_apt_rent_data(lawd_cd: str, deal_ymd: str, ctx: Optional[Any] = None) -> TextContent:
    """
    아파트 전월세 실거래가 데이터를 동별(byDong), 전세/월세 구분 통계+거래 리스트로 반환
    """
    result = get_apt_rent_data(lawd_cd, deal_ymd)
    return TextContent(type="text", text=result)

@mcp.tool(
    name="get_officetel_trade_data",
    description="""
이 도구를 사용하기 전에 반드시 먼저 법정동 코드(5자리, lawd_cd)를 조회하고 선택해야 합니다. 법정동 코드는 오피스텔 실거래가 데이터를 조회하는 데 필수입니다.

사용 절차 안내:
1. 먼저 'get_region_codes' 도구를 사용하여 원하는 지역의 법정동 코드(lawd_cd)를 조회하세요.
2. 조회한 lawd_cd(5자리)와 거래년월(deal_ymd, 6자리: YYYYMM)을 본 도구에 입력하여 오피스텔 매매 실거래가 데이터를 조회하세요.

동별(byDong)로 이미 거래+통계가 묶여 반환되므로, 별도의 동 필터링 도구 없이 원하는 동의 거래/통계를 바로 추출할 수 있습니다.

Arguments:
- lawd_cd (str, required): 법정동코드(5자리)
- deal_ymd (str, required): 거래년월(YYYYMM, 6자리)

Returns: 오피스텔 매매 실거래가 전체 거래+통계(byDong) JSON
""",
    tags={"오피스텔", "실거래가", "매매"}
)
def mcp_get_officetel_trade_data(lawd_cd: str, deal_ymd: str, ctx: Optional[Any] = None) -> TextContent:
    """
    오피스텔 매매 실거래가 데이터를 동별(byDong) 통계+거래 리스트로 반환
    """
    result = get_officetel_trade_data(lawd_cd, deal_ymd)
    return TextContent(type="text", text=result)

@mcp.tool(
    name="get_officetel_rent_data",
    description="""
이 도구를 사용하기 전에 반드시 먼저 법정동 코드(5자리, lawd_cd)를 조회하고 선택해야 합니다. 법정동 코드는 오피스텔 전월세 실거래가 데이터를 조회하는 데 필수입니다.

사용 절차 안내:
1. 먼저 'get_region_codes' 도구를 사용하여 원하는 지역의 법정동 코드(lawd_cd)를 조회하세요.
2. 조회한 lawd_cd(5자리)와 거래년월(deal_ymd, 6자리: YYYYMM)을 본 도구에 입력하여 오피스텔 전월세 실거래가 데이터를 조회하세요.

동별(byDong)로 전세/월세를 구분하여 거래+통계가 묶여 반환되므로, 별도의 동 필터링 도구 없이 원하는 동의 거래/통계를 바로 추출할 수 있습니다.

Arguments:
- lawd_cd (str, required): 법정동코드(5자리)
- deal_ymd (str, required): 거래년월(YYYYMM, 6자리)

Returns: 오피스텔 전월세 실거래가 전체 거래+통계(byDong, 전세/월세 구분) JSON
""",
    tags={"오피스텔", "전월세", "실거래가"}
)
def mcp_get_officetel_rent_data(lawd_cd: str, deal_ymd: str, ctx: Optional[Any] = None) -> TextContent:
    """
    오피스텔 전월세 실거래가 데이터를 동별(byDong), 전세/월세 구분 통계+거래 리스트로 반환
    """
    result = get_officetel_rent_data(lawd_cd, deal_ymd)
    return TextContent(type="text", text=result)

@mcp.tool(
    name="get_single_detached_house_trade_data",
    description="""
이 도구를 사용하기 전에 반드시 먼저 법정동 코드(5자리, lawd_cd)를 조회하고 선택해야 합니다. 법정동 코드는 단독/다가구 매매 실거래가 데이터를 조회하는 데 필수입니다.

사용 절차 안내:
1. 먼저 'get_region_codes' 도구를 사용하여 원하는 지역의 법정동 코드(lawd_cd)를 조회하세요.
2. 조회한 lawd_cd(5자리)와 거래년월(deal_ymd, 6자리: YYYYMM)을 본 도구에 입력하여 단독/다가구 매매 실거래가 데이터를 조회하세요.

동별(byDong)로 거래+통계가 묶여 반환되므로, 별도의 동 필터링 도구 없이 원하는 동의 거래/통계를 바로 추출할 수 있습니다.

Arguments:
- lawd_cd (str, required): 법정동코드(5자리)
- deal_ymd (str, required): 거래년월(YYYYMM, 6자리)

Returns: 단독/다가구 매매 실거래가 전체 거래+통계(byDong) JSON
""",
    tags={"단독다가구", "단독주택", "다가구주택", "실거래가", "매매"}
)
def get_single_detached_house_trade_data(lawd_cd: str, deal_ymd: str, ctx: Optional[Any] = None) -> TextContent:
    """
    단독/다가구 매매 실거래가 API 호출 및 전체 데이터 JSON+통계 반환
    """
    def call(context):
        return get_sh_trade_data(lawd_cd=lawd_cd, deal_ymd=deal_ymd)
    result = with_context(ctx, "get_single_detached_house_trade_data", call)
    return TextContent(type="text", text=result)

@mcp.tool(
    name="get_single_detached_house_rent_data",
    description="""
이 도구를 사용하기 전에 반드시 먼저 법정동 코드(5자리, lawd_cd)를 조회하고 선택해야 합니다. 법정동 코드는 단독/다가구 전월세 실거래가 데이터를 조회하는 데 필수입니다.

사용 절차 안내:
1. 먼저 'get_region_codes' 도구를 사용하여 원하는 지역의 법정동 코드(lawd_cd)를 조회하세요.
2. 조회한 lawd_cd(5자리)와 거래년월(deal_ymd, 6자리: YYYYMM)을 본 도구에 입력하여 단독/다가구 전월세 실거래가 데이터를 조회하세요.

동별(byDong)로 전세/월세를 구분하여 거래+통계가 묶여 반환되므로, 별도의 동 필터링 도구 없이 원하는 동의 거래/통계를 바로 추출할 수 있습니다.

Arguments:
- lawd_cd (str, required): 법정동코드(5자리)
- deal_ymd (str, required): 거래년월(YYYYMM, 6자리)

Returns: 단독/다가구 전월세 실거래가 전체 거래+통계(byDong, 전세/월세 구분) JSON
""",
    tags={"단독다가구", "단독주택", "다가구주택", "전월세", "실거래가"}
)
def get_single_detached_house_rent_data(lawd_cd: str, deal_ymd: str, ctx: Optional[Any] = None) -> TextContent:
    """
    단독/다가구 전월세 실거래가 API 호출 및 전체 데이터 JSON+통계 반환
    """
    def call(context):
        return get_sh_rent_data(lawd_cd=lawd_cd, deal_ymd=deal_ymd)
    result = with_context(ctx, "get_single_detached_house_rent_data", call)
    return TextContent(type="text", text=result)

@mcp.tool(
    name="get_row_house_trade_data",
    description="""
이 도구를 사용하기 전에 반드시 먼저 법정동 코드(5자리, lawd_cd)를 조회하고 선택해야 합니다. 법정동 코드는 연립다세대 실거래가 데이터를 조회하는 데 필수입니다.

사용 절차 안내:
1. 먼저 'get_region_codes' 도구를 사용하여 원하는 지역의 법정동 코드(lawd_cd)를 조회하세요.
2. 조회한 lawd_cd(5자리)와 거래년월(deal_ymd, 6자리: YYYYMM)을 본 도구에 입력하여 연립다세대 매매 실거래가 데이터를 조회하세요.

동별(byDong)로 이미 거래+통계가 묶여 반환되므로, 별도의 동 필터링 도구 없이 원하는 동의 거래/통계를 바로 추출할 수 있습니다.

Arguments:
- lawd_cd (str, required): 법정동코드(5자리)
- deal_ymd (str, required): 거래년월(YYYYMM, 6자리)

Returns: 연립다세대 매매 실거래가 전체 거래+통계(byDong) JSON
""",
    tags={"연립다세대", "실거래가", "매매"}
)
def get_row_house_trade_data(lawd_cd: str, deal_ymd: str, ctx: Optional[Any] = None) -> TextContent:
    """
    연립다세대 매매 실거래가 API 호출 및 전체 데이터 JSON+통계 반환
    """
    def call(context):
        return get_rh_trade_data(lawd_cd=lawd_cd, deal_ymd=deal_ymd)
    result = with_context(ctx, "get_row_house_trade_data", call)
    return TextContent(type="text", text=result)

@mcp.tool(
    name="get_row_house_rent_data",
    description="""
이 도구를 사용하기 전에 반드시 먼저 법정동 코드(5자리, lawd_cd)를 조회하고 선택해야 합니다. 법정동 코드는 연립다세대 전월세 실거래가 데이터를 조회하는 데 필수입니다.

사용 절차 안내:
1. 먼저 'get_region_codes' 도구를 사용하여 원하는 지역의 법정동 코드(lawd_cd)를 조회하세요.
2. 조회한 lawd_cd(5자리)와 거래년월(deal_ymd, 6자리: YYYYMM)을 본 도구에 입력하여 연립다세대 전월세 실거래가 데이터를 조회하세요.

동별(byDong)로 전세/월세를 구분하여 거래+통계가 묶여 반환되므로, 별도의 동 필터링 도구 없이 원하는 동의 거래/통계를 바로 추출할 수 있습니다.

Arguments:
- lawd_cd (str, required): 법정동코드(5자리)
- deal_ymd (str, required): 거래년월(YYYYMM, 6자리)

Returns: 연립다세대 전월세 실거래가 전체 거래+통계(byDong, 전세/월세 구분) JSON
""",
    tags={"연립다세대", "전월세", "실거래가"}
)
def get_row_house_rent_data(lawd_cd: str, deal_ymd: str, ctx: Optional[Any] = None) -> TextContent:
    """
    연립다세대 전월세 실거래가 API 호출 및 전체 데이터 JSON+통계 반환
    """
    def call(context):
        return get_rh_rent_data(lawd_cd=lawd_cd, deal_ymd=deal_ymd)
    result = with_context(ctx, "get_row_house_rent_data", call)
    return TextContent(type="text", text=result) 