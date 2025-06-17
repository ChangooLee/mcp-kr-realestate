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
    name="get_nrg_trade_data",
    description="""
Before using this tool, you MUST first look up and select the correct legal district code (lawd_cd, 5 digits) for the target area. This is required to retrieve actual real estate transaction prices.

Usage guide:
1. First, use a tool or resource to search for and obtain the lawd_cd (legal district code) for your desired region.
2. Then, call this tool with the lawd_cd (5 digits) and deal_ymd (YYYYMM, 6 digits).

Arguments:
- lawd_cd (str, required): Legal district code (법정동코드), exactly 5 digits.
- deal_ymd (str, required): Transaction year and month (YYYYMM), exactly 6 digits.

Returns: Path to the saved XML file containing the real estate transaction data.
""",
    tags={"실거래가", "상업업무용"}
)
def get_nrg_trade_data(lawd_cd: str, deal_ymd: str, ctx: Optional[Any] = None) -> TextContent:
    """
    상업업무용 부동산 매매 실거래가 API 호출 및 XML 저장
    Args:
        lawd_cd (str): 법정동코드 5자리
        deal_ymd (str): 거래년월 (YYYYMM)
    Returns:
        TextContent: 저장된 XML 파일 경로
    """
    def call(context):
        api_key = os.environ.get("PUBLIC_DATA_API_KEY_ENCODED")
        if not api_key:
            raise ValueError("환경변수 PUBLIC_DATA_API_KEY_ENCODED가 설정되어 있지 않습니다.")
        base_url = "http://apis.data.go.kr/1613000/RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade"
        params = {'LAWD_CD': lawd_cd, 'DEAL_YMD': deal_ymd, 'stdt': deal_ymd[:4]}
        data = None
        curl_path = shutil.which("curl")
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        curl_url = f"https://apis.data.go.kr/1613000/RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade?LAWD_CD={lawd_cd}&DEAL_YMD={deal_ymd}&serviceKey={api_key}"
        if curl_path:
            try:
                result = subprocess.run([
                    curl_path, "-s", "-H", f"User-Agent: {user_agent}", curl_url
                ], capture_output=True, text=True, check=True)
                data = result.stdout
            except Exception as e:
                logger.warning(f"curl subprocess failed: {e}. Falling back to requests.")
        if data is None:
            try:
                response = requests.get(
                    base_url, params=params, headers={"User-Agent": user_agent}, verify=False, timeout=30
                )
                response.raise_for_status()
                data = response.text
            except Exception as e:
                raise RuntimeError(f"Both curl and requests failed to fetch data: {e}")
        data_dir = Path(__file__).parent.parent / "utils" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        file_path = data_dir / f"NRG_{lawd_cd}_{deal_ymd}.xml"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(data)
        return str(file_path)
    result = with_context(ctx, "get_nrg_trade_data", call)
    return TextContent(type="text", text=result)

@mcp.tool(
    name="parse_nrg_trade_xml",
    description="상업업무용 실거래가 XML을 JSON 리스트로 파싱하고, 주요 통계(거래건수, 거래금액 평균/최대/최소 등)를 함께 반환합니다. 거래금액 단위는 만원입니다.",
    tags={"실거래가", "XML파싱"}
)
def parse_nrg_trade_xml(xml_path: str, ctx: Optional[Any] = None) -> TextContent:
    def call(context):
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            items = []
            for item in root.findall('.//item'):
                row = {child.tag: child.text for child in item}
                items.append(row)
            if not items:
                return json.dumps({"data": [], "summary": {"message": "거래 데이터가 없습니다."}}, ensure_ascii=False)
            df = pd.DataFrame(items)
            # 숫자형 변환
            def to_num(s):
                try:
                    return float(str(s).replace(',', ''))
                except:
                    return np.nan
            df['dealAmountNum'] = df.get('거래금액', df.get('dealAmount', np.nan)).map(to_num)
            df['buildingArNum'] = df.get('전용면적', df.get('buildingAr', np.nan)).map(to_num)
            df['buildYearNum'] = df.get('건축년도', df.get('buildYear', np.nan)).map(to_num)
            df['dealDayNum'] = df.get('일', df.get('dealDay', np.nan)).map(to_num)
            # 동별
            byDong = []
            for dong, group in df.groupby(df.get('법정동', df.get('umdNm', 'dong'))):
                group = group.dropna(subset=['dealAmountNum'])
                if len(group) == 0: continue
                byDong.append({
                    'dong': dong,
                    'count': int(len(group)),
                    'avgAmount': float(group['dealAmountNum'].mean()),
                    'maxAmount': float(group['dealAmountNum'].max()),
                    'minAmount': float(group['dealAmountNum'].min()),
                })
            # 건물 용도별
            byBuildingUse = []
            for use, group in df.groupby(df.get('건물용도', df.get('buildingUse', 'use'))):
                group = group.dropna(subset=['dealAmountNum'])
                if len(group) == 0: continue
                byBuildingUse.append({
                    'use': use,
                    'count': int(len(group)),
                    'totalAmount': float(group['dealAmountNum'].sum()),
                    'avgAmount': float(group['dealAmountNum'].mean()),
                })
            # 구매자 유형별
            byBuyer = []
            for buyer, group in df.groupby(df.get('구매자구분', df.get('buyerGbn', 'buyer'))):
                group = group.dropna(subset=['dealAmountNum'])
                if len(group) == 0: continue
                byBuyer.append({
                    'buyer': buyer,
                    'count': int(len(group)),
                    'totalAmount': float(group['dealAmountNum'].sum()),
                    'avgAmount': float(group['dealAmountNum'].mean()),
                })
            # 일별
            byDay = []
            for day, group in df.groupby('dealDayNum'):
                group = group.dropna(subset=['dealAmountNum'])
                if len(group) == 0: continue
                byDay.append({
                    'day': int(day) if not np.isnan(day) else None,
                    'count': int(len(group)),
                    'totalAmount': float(group['dealAmountNum'].sum()),
                    'avgAmount': float(group['dealAmountNum'].mean()),
                })
            byDay = sorted(byDay, key=lambda x: (x['day'] if x['day'] is not None else 0))
            # 전체
            total = {
                'count': int(len(df)),
                'avgAmount': float(df['dealAmountNum'].mean()),
                'maxAmount': float(df['dealAmountNum'].max()),
                'minAmount': float(df['dealAmountNum'].min()),
            }
            summary = {
                'amountUnit': '만원',
                'total': total,
                'byDong': byDong,
                'byBuildingUse': byBuildingUse,
                'byBuyer': byBuyer,
                'byDay': byDay
            }
            result = {"data": items, "summary": summary}
            file_logger.info(f"parse_nrg_trade_xml 정상 처리: {summary}")
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            file_logger.exception(f"parse_nrg_trade_xml: 치명적 오류: {e}")
            return json.dumps({"data": [], "summary": {"error": f"[오류] XML 파싱 중 문제가 발생했습니다: {e}"}}, ensure_ascii=False)
    result = with_context(ctx, "parse_nrg_trade_xml", call)
    # MCP TextContent only supports type='text', so we return JSON as a string
    return TextContent(type="text", text=result) 