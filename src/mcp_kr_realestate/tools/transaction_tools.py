"""
실거래가 조회/분석 도구

예시 사용법:

from mcp_kr_realestate.tools.transaction_tools import parse_nrg_trade_xml, summarize_nrg_trade

df = parse_nrg_trade_xml('mcp_kr_realestate/utils/data/NRG_11680_202506.xml')
summary = summarize_nrg_trade(df)
print(summary)
"""

import logging
import json
from pathlib import Path
import pandas as pd
import xml.etree.ElementTree as ET
import requests
from typing import Any, Callable, Optional, List
import os

from ..server import mcp, ctx, RealEstateContext
from mcp.types import TextContent
from ..utils.ctx_helper import with_context
from ..utils.region_codes import get_region_code_df
from mcp_kr_realestate.utils.data_processor import get_cache_dir

# 각 API 모듈로부터 함수를 직접 임포트
from ..apis.apt_rent import get_apt_rent_data as api_get_apt_rent
from ..apis.apt_trade import get_apt_trade_data as api_get_apt_trade
from ..apis.land_trade import get_land_trade_data as api_get_land_trade
from ..apis.indutrade import get_indu_trade_data as api_get_indu_trade
from ..apis.officetel_rent import get_officetel_rent_data as api_get_officetel_rent
from ..apis.officetel_trade import get_officetel_trade_data as api_get_officetel_trade
from ..apis.rh_rent import get_rh_rent_data as api_get_rh_rent
from ..apis.rh_trade import get_rh_trade_data as api_get_rh_trade
from ..apis.sh_rent import get_sh_rent_data as api_get_sh_rent
from ..apis.sh_trade import get_sh_trade_data as api_get_sh_trade

logger = logging.getLogger(__name__)

def _fetch_and_save_as_json(
    api_func: Callable[[str, str], str],
    file_prefix: str,
    region_code: str,
    year_month: str,
    target_dir: Optional[str] = None
) -> str:
    """
    공통: API 함수로부터 받은 데이터를 DataFrame으로 저장하고 경로 반환
    """
    # 항상 src/mcp_kr_realestate/utils/cache/raw_data에 저장
    if target_dir is None:
        data_dir = Path(__file__).parent.parent / "utils" / "cache" / "raw_data"
    else:
        data_dir = Path(target_dir) / "raw_data"
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        # API 함수 호출 (결과는 통계가 포함된 JSON 문자열)
        response_json_str = api_func(region_code, year_month)
        response_data = json.loads(response_json_str)

        # 'deals' 키가 있는지 확인하여 거래 데이터 추출
        all_deals = []
        if 'byDong' in response_data and response_data['byDong']:
            for dong_data in response_data['byDong']:
                # 매매(기존)
                if 'deals' in dong_data and dong_data['deals']:
                    all_deals.extend(dong_data['deals'])
                # 전월세(jeonse/wolse) 구조 지원
                if 'jeonse' in dong_data and dong_data['jeonse']:
                    if 'deals' in dong_data['jeonse'] and dong_data['jeonse']['deals']:
                        all_deals.extend(dong_data['jeonse']['deals'])
                if 'wolse' in dong_data and dong_data['wolse']:
                    if 'deals' in dong_data['wolse'] and dong_data['wolse']['deals']:
                        all_deals.extend(dong_data['wolse']['deals'])
        elif 'deals' in response_data: # 루트 레벨에 deals가 있는 경우
             all_deals = response_data['deals']

        if not all_deals:
            logger.warning(f"거래 데이터 없음: {file_prefix}, {region_code}, {year_month}")
            return json.dumps({"error": "No transaction data available for the given criteria.", "criteria": {"region_code": region_code, "year_month": year_month}})
        
        df = pd.DataFrame(all_deals)

        # 파일 경로 및 디렉토리 설정 (utils/cache/raw_data)
        file_name = f"{file_prefix}_{region_code}_{year_month}.raw.data.json"
        file_path = data_dir / file_name

        # DataFrame을 JSON으로 저장 (레코드 기반, 각 줄이 하나의 JSON 객체)
        df.to_json(file_path, orient='records', lines=True, force_ascii=False)
        
        logger.info(f"✅ Raw 데이터 저장 완료: {file_path}")
        return str(file_path)

    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 실패: {response_json_str[:200]}... - {e}", exc_info=True)
        return json.dumps({"error": f"Failed to parse JSON response: {e}"})
    except Exception as e:
        logger.error(f"데이터 처리 중 알 수 없는 오류: {e}", exc_info=True)
        return json.dumps({"error": f"An unknown error occurred: {e}"})

def _load_region_codes_json(json_path: Optional[str] = None) -> list:
    """
    region_codes.json 파일을 로드하거나, 없으면 DataFrame에서 생성 후 저장
    """
    if json_path is None:
        json_path = os.path.join(os.path.dirname(__file__), '../utils/data/region_codes.json')
        json_path = os.path.abspath(json_path)
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    # 없으면 DataFrame에서 생성 후 저장
    df = get_region_code_df()
    records = df[['법정동코드', '시도명', '시군구명', '읍면동명']].to_dict(orient='records')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False)
    return records

@mcp.tool(
    name="get_region_codes",
    description="""입력한 지역명(region_name)으로 법정동 코드 목록을 반환합니다.\n- `region_name`: 구/동/시 등 지역 이름의 일부를 입력합니다.\n검색 결과가 많을 경우 미리보기(10건)만 반환하며, 전체 목록이 필요하면 별도 파일로 저장됩니다.""",
    tags={"부동산", "실거래가", "지역코드"}
)
def get_region_codes(region_name: str) -> TextContent:
    """
    입력한 지역명(region_name)으로 법정동 코드 목록을 반환합니다. (10건 초과시 미리보기/요약)
    """
    try:
        records = _load_region_codes_json()
        filtered = [r for r in records if (
            (region_name in (r.get('시도명') or '')) or
            (region_name in (r.get('시군구명') or '')) or
            (region_name in (r.get('읍면동명') or ''))
        )]
        total_count = len(filtered)
        preview = filtered[:5]
        if total_count == 0:
            return TextContent(type="text", text=json.dumps({"error": f"'{region_name}'(으)로 일치하는 법정동 코드가 없습니다."}, ensure_ascii=False))
        result = {
            "total_count": total_count,
            "preview": preview,
        }
        if total_count > 5:
            result["message"] = f"검색 결과가 {total_count}건입니다. 미리보기 5건만 표시합니다. 전체 목록이 필요하면 '상세코드'로 별도 요청하세요."
        return TextContent(type="text", text=json.dumps(result, ensure_ascii=False))
    except Exception as e:
        return TextContent(type="text", text=json.dumps({"error": f"법정동 코드 조회 중 오류: {e}"}, ensure_ascii=False))

@mcp.tool(
    name="get_commercial_property_trade_data",
    description="""상업업무용 부동산 매매 실거래 데이터를 조회하여 파일로 저장하고, 그 경로를 반환합니다.
- `region_code`: `get_region_codes`로 얻은 5자리 지역 코드를 사용합니다.
- `year_month`: 'YYYYMM' 형식의 년월을 사용합니다.
""",
    tags={"부동산", "실거래가", "상업업무용", "매매"}
)
def get_commercial_property_trade_data(region_code: str, year_month: str, ctx: Optional[Any] = None) -> TextContent:
    # NRGTradeAPI는 context를 통해 호출해야 함
    def call(context: RealEstateContext):
        return context.nrg_trade.get_trade_data(lawd_cd=region_code, deal_ymd=year_month)
    
    response_str = with_context(ctx, "get_commercial_property_trade_data", call)
    
    # 공통 로직을 사용하기 위해 약간의 조정
    def dummy_api_call(rc, ym):
        return response_str

    file_path_or_error = _fetch_and_save_as_json(dummy_api_call, "NRG_TRADE", region_code, year_month)
    return TextContent(type="text", text=file_path_or_error)

@mcp.tool(
    name="get_single_detached_house_trade_data",
    description="""단독/다가구 매매 실거래가 데이터를 조회합니다.
- `region_code`: `get_region_codes`로 얻은 5자리 지역 코드를 사용합니다.
- `year_month`: 'YYYYMM' 형식의 년월을 사용합니다.
""",
    tags={"부동산", "실거래가", "단독다가구", "매매"}
)
def get_single_detached_house_trade_data(region_code: str, year_month: str) -> TextContent:
    result = _fetch_and_save_as_json(api_get_sh_trade, "SINGLE_DETACHED_HOUSE_TRADE", region_code, year_month)
    return TextContent(type="text", text=result)

@mcp.tool(
    name="get_single_detached_house_rent_data",
    description="""단독/다가구 전월세 실거래가 데이터를 조회합니다.
- `region_code`: `get_region_codes`로 얻은 5자리 지역 코드를 사용합니다.
- `year_month`: 'YYYYMM' 형식의 년월을 사용합니다.
""",
    tags={"부동산", "실거래가", "단독다가구", "전월세"}
)
def get_single_detached_house_rent_data(region_code: str, year_month: str) -> TextContent:
    result = _fetch_and_save_as_json(api_get_sh_rent, "SINGLE_DETACHED_HOUSE_RENT", region_code, year_month)
    return TextContent(type="text", text=result)

@mcp.tool(
    name="get_row_house_trade_data",
    description="""연립다세대 매매 실거래가 데이터를 조회합니다.
- `region_code`: `get_region_codes`로 얻은 5자리 지역 코드를 사용합니다.
- `year_month`: 'YYYYMM' 형식의 년월을 사용합니다.
""",
    tags={"부동산", "실거래가", "연립다세대", "매매"}
)
def get_row_house_trade_data(region_code: str, year_month: str) -> TextContent:
    result = _fetch_and_save_as_json(api_get_rh_trade, "ROW_HOUSE_TRADE", region_code, year_month)
    return TextContent(type="text", text=result)

@mcp.tool(
    name="get_row_house_rent_data",
    description="""연립/다세대 전월세 실거래가 데이터를 조회합니다.
- `region_code`: `get_region_codes`로 얻은 5자리 지역 코드를 사용합니다.
- `year_month`: 'YYYYMM' 형식의 년월을 사용합니다.
""",
    tags={"부동산", "실거래가", "연립다세대", "전월세"}
)
def get_row_house_rent_data(region_code: str, year_month: str) -> TextContent:
    result = _fetch_and_save_as_json(api_get_rh_rent, "ROW_HOUSE_RENT", region_code, year_month)
    return TextContent(type="text", text=result)

@mcp.tool(
    name="get_industrial_property_trade_data",
    description="""공장/창고 등 산업용 부동산 매매 실거래가 데이터를 조회합니다.
- `region_code`: `get_region_codes`로 얻은 5자리 지역 코드를 사용합니다.
- `year_month`: 'YYYYMM' 형식의 년월을 사용합니다.
""",
    tags={"부동산", "실거래가", "산업용", "공장", "창고", "매매"}
)
def get_industrial_property_trade_data(region_code: str, year_month: str) -> TextContent:
    result = _fetch_and_save_as_json(api_get_indu_trade, "INDU_TRADE", region_code, year_month)
    return TextContent(type="text", text=result)

# 아파트 매매 조회
@mcp.tool(
    name="get_apt_trade_data",
    description="""아파트 매매 실거래가 데이터를 조회합니다.
- `region_code`: `get_region_codes`로 얻은 5자리 지역 코드를 사용합니다.
- `year_month`: 'YYYYMM' 형식의 년월을 사용합니다.
""",
    tags={"부동산", "실거래가", "아파트", "매매"}
)
def get_apt_trade_data(region_code: str, year_month: str) -> TextContent:
    result = _fetch_and_save_as_json(api_get_apt_trade, "APT_TRADE", region_code, year_month)
    return TextContent(type="text", text=result)

# 아파트 전월세 조회
@mcp.tool(
    name="get_apt_rent_data",
    description="""아파트 전월세 실거래가 데이터를 조회합니다.
- `region_code`: `get_region_codes`로 얻은 5자리 지역 코드를 사용합니다.
- `year_month`: 'YYYYMM' 형식의 년월을 사용합니다.
""",
    tags={"부동산", "실거래가", "아파트", "전월세", "전세", "월세"}
)
def get_apt_rent_data(region_code: str, year_month: str) -> TextContent:
    result = _fetch_and_save_as_json(api_get_apt_rent, "APT_RENT", region_code, year_month)
    return TextContent(type="text", text=result)

# 오피스텔 매매 조회
@mcp.tool(
    name="get_officetel_trade_data",
    description="""오피스텔 매매 실거래가 데이터를 조회합니다.
- `region_code`: `get_region_codes`로 얻은 5자리 지역 코드를 사용합니다.
- `year_month`: 'YYYYMM' 형식의 년월을 사용합니다.
""",
    tags={"부동산", "실거래가", "오피스텔", "매매"}
)
def get_officetel_trade_data(region_code: str, year_month: str) -> TextContent:
    result = _fetch_and_save_as_json(api_get_officetel_trade, "OFFICETEL_TRADE", region_code, year_month)
    return TextContent(type="text", text=result)

# 오피스텔 전월세 조회
@mcp.tool(
    name="get_officetel_rent_data",
    description="""오피스텔 전월세 실거래가 데이터를 조회합니다.
- `region_code`: `get_region_codes`로 얻은 5자리 지역 코드를 사용합니다.
- `year_month`: 'YYYYMM' 형식의 년월을 사용합니다.
""",
    tags={"부동산", "실거래가", "오피스텔", "전월세"}
)
def get_officetel_rent_data(region_code: str, year_month: str) -> TextContent:
    result = _fetch_and_save_as_json(api_get_officetel_rent, "OFFICETEL_RENT", region_code, year_month)
    return TextContent(type="text", text=result)

# 토지 매매 조회
@mcp.tool(
    name="get_land_trade_data",
    description="""토지 매매 실거래가 데이터를 조회합니다.
- `region_code`: `get_region_codes`로 얻은 5자리 지역 코드를 사용합니다.
- `year_month`: 'YYYYMM' 형식의 년월을 사용합니다.
""",
    tags={"부동산", "실거래가", "토지", "매매"}
)
def get_land_trade_data(region_code: str, year_month: str) -> TextContent:
    result = _fetch_and_save_as_json(api_get_land_trade, "LAND_TRADE", region_code, year_month)
    return TextContent(type="text", text=result)

@mcp.tool(
    name="get_transaction_cache_data",
    description="""
    Load cached real estate transaction data (raw_data) for any asset type (apartment, officetel, row house, single detached, land, industrial, etc.), region, and months, and filter by any field (e.g., apartment name, officetel name, etc.).
    - asset_type: 'APT_TRADE', 'APT_RENT', 'OFFICETEL_TRADE', 'OFFICETEL_RENT', 'ROW_HOUSE_TRADE', 'ROW_HOUSE_RENT', 'SINGLE_DETACHED_HOUSE_TRADE', 'SINGLE_DETACHED_HOUSE_RENT', 'LAND_TRADE', 'INDU_TRADE', ...
    - region_code: 5-digit legal dong code
    - year_months: list of 'YYYYMM' (multiple months allowed)
    - field_name: (optional) name of the field to filter (e.g., 'aptNm', 'officetelNm', 'rowHouseNm', etc.)
    - field_value_substring: (optional) substring to search for in the field
    Returns a preview (10 rows), total count, unique values for the filtered field, and cache files. Only summary/preview is returned for LLM efficiency. Works for all asset types and both trade and rent types.
    """,
    tags={"부동산", "실거래가", "캐시", "검색", "요약", "매매", "전월세", "임대", "임차"}
)
def get_transaction_cache_data(asset_type: str, region_code: str, year_months: List[str], field_name: Optional[str] = None, field_value_substring: Optional[str] = None) -> TextContent:
    """
    Load cached transaction data for any asset type, region, and months, with optional filtering by any field (e.g., apartment name, officetel name, etc.).
    """
    import pandas as pd
    from pathlib import Path
    import json
    import os

    cache_dir = Path(__file__).parent.parent / "utils" / "cache" / "raw_data"
    dfs = []
    for ym in year_months:
        fname = f"{asset_type}_{region_code}_{ym}.raw.data.json"
        fpath = cache_dir / fname
        if fpath.exists():
            try:
                df = pd.read_json(fpath, lines=True)
                df["_cache_file"] = str(fpath)
                dfs.append(df)
            except Exception as e:
                continue
    if not dfs:
        return TextContent(type="text", text=json.dumps({"error": "No cached data found for the given criteria."}, ensure_ascii=False))
    df_all = pd.concat(dfs, ignore_index=True)
    # Optional generic field filter
    if field_name and field_value_substring:
        if field_name in df_all.columns:
            df_all = df_all[df_all[field_name].astype(str).str.contains(field_value_substring, na=False)]
    preview = df_all.head(10).to_dict(orient="records")
    unique_values = list(df_all[field_name].dropna().unique()) if field_name and field_name in df_all.columns else []
    result = {
        "total_count": len(df_all),
        "preview": preview,
        "unique_values_for_field": unique_values,
        "cache_files": list(set(df_all["_cache_file"]))
    }
    def normalize_amount(val):
        # Convert to integer 원 단위 (만원 * 10,000)
        if isinstance(val, str):
            v = val.replace(",", "")
            if v.replace(".", "").isdigit():
                return int(float(v) * 10000)
            return val
        if isinstance(val, (float, int)):
            return int(round(val * 10000))
        return val
    for row in preview:
        if "dealAmount" in row:
            row["dealAmount"] = normalize_amount(row["dealAmount"])
        if "dealAmountNum" in row:
            row["dealAmountNum"] = normalize_amount(row["dealAmountNum"])
    return TextContent(type="text", text=json.dumps(result, ensure_ascii=False)) 