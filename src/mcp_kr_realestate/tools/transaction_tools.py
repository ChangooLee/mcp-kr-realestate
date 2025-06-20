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
    name="get_nrg_trade_data",
    description="""
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
    tags={"실거래가", "상업업무용"}
)
def get_nrg_trade_data(lawd_cd: str, deal_ymd: str, ctx: Optional[Any] = None) -> TextContent:
    """
    상업업무용 부동산 매매 실거래가 API 호출 및 전체 데이터 JSON+통계 반환 (curl subprocess + requests fallback, 반복 수집)
    Args:
        lawd_cd (str): 법정동코드 5자리
        deal_ymd (str): 거래년월 (YYYYMM)
    Returns:
        TextContent: 전체 거래 데이터와 통계가 포함된 JSON 문자열
    """
    def call(context):
        api_key = os.environ.get("PUBLIC_DATA_API_KEY_ENCODED")
        if not api_key:
            raise ValueError("환경변수 PUBLIC_DATA_API_KEY_ENCODED가 설정되어 있지 않습니다.")
        base_url = "http://apis.data.go.kr/1613000/RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade"
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        curl_path = shutil.which("curl")
        num_of_rows = 100
        all_items = []
        total_count = None
        page_no = 1
        while True:
            params = {
                'LAWD_CD': lawd_cd,
                'DEAL_YMD': deal_ymd,
                'serviceKey': api_key,
                'numOfRows': num_of_rows,
                'pageNo': page_no
            }
            curl_url = f"{base_url}?LAWD_CD={lawd_cd}&DEAL_YMD={deal_ymd}&serviceKey={api_key}&numOfRows={num_of_rows}&pageNo={page_no}"
            data = None
            if curl_path:
                try:
                    result = subprocess.run([
                        curl_path, "-s", "-H", f"User-Agent: {user_agent}", curl_url
                    ], capture_output=True, text=True, check=True)
                    data = result.stdout
                except Exception:
                    pass  # fallback to requests
            if data is None:
                try:
                    response = requests.get(
                        base_url, params=params, headers={"User-Agent": user_agent}, verify=False, timeout=30
                    )
                    response.raise_for_status()
                    data = response.text
                except Exception as e:
                    raise RuntimeError(f"Both curl and requests failed to fetch data: {e}")
            # XML 파싱
            root = ET.fromstring(data)
            if total_count is None:
                try:
                    tc_text = root.findtext('.//totalCount')
                    if tc_text is not None and tc_text.strip() != '':
                        total_count = int(tc_text)
                    else:
                        total_count = 0
                except Exception:
                    total_count = 0
            items = root.findall('.//item')
            all_items.extend(items)
            if len(all_items) >= total_count or not items:
                break
            page_no += 1
        # XML -> JSON 변환
        records = []
        for item in all_items:
            row = {child.tag: child.text for child in item}
            records.append(row)
        if not records:
            return TextContent(type="text", text=json.dumps({"byDong": [], "meta": {"lawd_cd": lawd_cd, "deal_ymd": deal_ymd, "totalCount": 0}}, ensure_ascii=False))
        df = pd.DataFrame(records)
        def to_num(s):
            try:
                return float(str(s).replace(',', ''))
            except:
                return np.nan
        def to_eok(val):
            try:
                return round(float(val) / 10000, 2) if val is not None and not np.isnan(val) else None
            except:
                return None
        def get_col(df, *names):
            for name in names:
                if name in df.columns:
                    return df[name]
            return pd.Series(np.nan, index=df.index)
        df['dealAmountNum'] = get_col(df, '거래금액', 'dealAmount').map(to_num)
        dong_col = get_col(df, '법정동', 'umdNm', 'dong')
        byDong = []
        for dong, group in df.groupby(dong_col):
            group = group.dropna(subset=['dealAmountNum'])
            if len(group) == 0: continue
            avg = float(group['dealAmountNum'].mean())
            mx = float(group['dealAmountNum'].max())
            mn = float(group['dealAmountNum'].min())
            deals = group.to_dict(orient='records')
            byDong.append({
                'dong': dong,
                'count': int(len(group)),
                'avgAmount': avg,
                'avgAmountEok': to_eok(avg),
                'maxAmount': mx,
                'maxAmountEok': to_eok(mx),
                'minAmount': mn,
                'minAmountEok': to_eok(mn),
                'deals': deals
            })
        meta = {"lawd_cd": lawd_cd, "deal_ymd": deal_ymd, "totalCount": total_count}
        result = {"byDong": byDong, "meta": meta}
        # (옵션) 원본 XML 저장
        data_dir = Path(__file__).parent.parent / "utils" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        file_path = data_dir / f"NRG_{lawd_cd}_{deal_ymd}.xml"
        response = ET.Element('response')
        header = ET.SubElement(response, 'header')
        ET.SubElement(header, 'resultCode').text = '000'
        ET.SubElement(header, 'resultMsg').text = 'OK'
        body = ET.SubElement(response, 'body')
        items_elem = ET.SubElement(body, 'items')
        for item in all_items:
            items_elem.append(item)
        ET.SubElement(body, 'numOfRows').text = str(num_of_rows)
        ET.SubElement(body, 'pageNo').text = '1'
        ET.SubElement(body, 'totalCount').text = str(total_count if total_count is not None else len(all_items))
        xml_str = ET.tostring(response, encoding='utf-8', method='xml').decode('utf-8')
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(xml_str)
        return TextContent(type="text", text=json.dumps(result, ensure_ascii=False))
    result = with_context(ctx, "get_nrg_trade_data", call)
    return result

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
    name="get_indu_trade_data",
    description="""
이 도구를 사용하기 전에 반드시 먼저 법정동 코드(5자리, lawd_cd)를 조회하고 선택해야 합니다. 법정동 코드는 공장 및 창고 등 부동산 실거래가 데이터를 조회하는 데 필수입니다.

사용 절차 안내:
1. 먼저 'get_region_codes' 도구를 사용하여 원하는 지역의 법정동 코드(lawd_cd)를 조회하세요.
2. 조회한 lawd_cd(5자리)와 거래년월(deal_ymd, 6자리: YYYYMM)을 본 도구에 입력하여 공장 및 창고 등 부동산 매매 실거래가 데이터를 조회하세요.

동별(byDong)로 이미 거래+통계가 묶여 반환되므로, 별도의 동 필터링 도구 없이 원하는 동의 거래/통계를 바로 추출할 수 있습니다.

Arguments:
- lawd_cd (str, required): 법정동코드(5자리)
- deal_ymd (str, required): 거래년월(YYYYMM, 6자리)

Returns: 공장 및 창고 등 부동산 매매 실거래가 전체 거래+통계(byDong) JSON
""",
    tags={"공장창고", "실거래가", "매매"}
)
def mcp_get_indu_trade_data(lawd_cd: str, deal_ymd: str, ctx: Optional[Any] = None) -> TextContent:
    """
    공장 및 창고 등 부동산 매매 실거래가 데이터를 동별(byDong) 통계+거래 리스트로 반환
    """
    result = get_indu_trade_data(lawd_cd, deal_ymd)
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
    name="get_sh_trade_data",
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
    tags={"단독다가구", "실거래가", "매매"}
)
def mcp_get_sh_trade_data(lawd_cd: str, deal_ymd: str, ctx: Optional[Any] = None) -> TextContent:
    """
    단독/다가구 매매 실거래가 데이터를 동별(byDong) 통계+거래 리스트로 반환
    """
    result = get_sh_trade_data(lawd_cd, deal_ymd)
    return TextContent(type="text", text=result)

@mcp.tool(
    name="get_sh_rent_data",
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
    tags={"단독다가구", "전월세", "실거래가"}
)
def mcp_get_sh_rent_data(lawd_cd: str, deal_ymd: str, ctx: Optional[Any] = None) -> TextContent:
    """
    단독/다가구 전월세 실거래가 데이터를 동별(byDong), 전세/월세 구분 통계+거래 리스트로 반환
    """
    result = get_sh_rent_data(lawd_cd, deal_ymd)
    return TextContent(type="text", text=result)

@mcp.tool(
    name="get_rh_trade_data",
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
def mcp_get_rh_trade_data(lawd_cd: str, deal_ymd: str, ctx: Optional[Any] = None) -> TextContent:
    """
    연립다세대 매매 실거래가 데이터를 동별(byDong) 통계+거래 리스트로 반환
    """
    result = get_rh_trade_data(lawd_cd, deal_ymd)
    return TextContent(type="text", text=result)

@mcp.tool(
    name="get_rh_rent_data",
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
def mcp_get_rh_rent_data(lawd_cd: str, deal_ymd: str, ctx: Optional[Any] = None) -> TextContent:
    """
    연립다세대 전월세 실거래가 데이터를 동별(byDong), 전세/월세 구분 통계+거래 리스트로 반환
    """
    result = get_rh_rent_data(lawd_cd, deal_ymd)
    return TextContent(type="text", text=result) 