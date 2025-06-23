"""
부동산 데이터 분석 및 통계 리포팅 도구
"""

import logging
import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
from pathlib import Path
import json
from typing import Any, Optional, Dict
from datetime import datetime

from mcp_kr_realestate.server import mcp
from mcp_kr_realestate.utils.ctx_helper import with_context
from mcp.types import TextContent

logger = logging.getLogger("mcp-kr-realestate")

# --- Helper Functions ---
def default_serializer(o):
    """JSON 직렬화를 위한 기본 serializer. numpy 타입을 python 타입으로 변환합니다."""
    if isinstance(o, (np.integer, np.floating)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, pd.Timestamp):
        return o.isoformat()
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

def to_numeric(series: pd.Series) -> pd.Series:
    """Helper function to convert series to numeric, handling commas."""
    return pd.to_numeric(series.astype(str).str.replace(',', ''), errors='coerce')

def format_unit(value, unit_str, precision=0):
    """Helper function to format a numeric value with a unit string."""
    if pd.isna(value):
        return None
    return f"{value:,.{precision}f} {unit_str}"

def clean_deal_for_display(series):
    """Cleans a deal (pandas Series) for JSON output."""
    deal_dict = series.where(pd.notna(series), None).to_dict()
    
    # Format date
    try:
        deal_dict['dealDate'] = f"{deal_dict.get('dealYear')}-{str(deal_dict.get('dealMonth','')).zfill(2)}-{str(deal_dict.get('dealDay','')).zfill(2)}"
    except (TypeError, ValueError):
        deal_dict['dealDate'] = None

    # Remove intermediate columns
    cols_to_remove = ['거래금액_num', '전용면적_num', '건축년도_num', '평당가_만원', '건물연령', '건물연령대', '건물규모', 'dealYear', 'dealMonth', 'dealDay']
    for col in cols_to_remove:
        deal_dict.pop(col, None)
        
    return deal_dict

def get_col_from_df(df, *col_names):
    """DataFrame과 여러 컬럼 이름을 받아, 존재하는 첫 번째 컬럼을 Series로 반환합니다."""
    for col in col_names:
        if col in df.columns:
            return df[col]
    # 어떤 컬럼도 찾지 못한 경우, None으로 채워진 Series를 반환하여 이후 연산에서 오류가 나지 않도록 합니다.
    return pd.Series([None] * len(df), index=df.index, dtype=object)

def get_summary_cache_path(p: Path, property_type: Optional[str] = None, trade_type: Optional[str] = None) -> Path:
    """
    property_type: 'commercial', 'land', 'industrial', 'apartment', 'officetel', 'row_house', 'single_detached', ...
    trade_type: 'trade', 'rent', None
    """
    cache_dir = p.parent.parent / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    # 상업/토지/창고(산업용)는 매매/전월세 구분 없이 하나의 summary
    if property_type in {"commercial", "land", "industrial"}:
        return cache_dir / f"{p.stem}_summary.json"
    # 그 외는 매매/전월세별로 분리
    if trade_type:
        return cache_dir / f"{p.stem}_{trade_type}_summary.json"
    return cache_dir / f"{p.stem}_summary.json"

def analyze_commercial_property_data(df: pd.DataFrame) -> Dict[str, Any]:
    """DataFrame을 받아 상업업무용 부동산 통계를 분석하고 영문 key와 단위가 포함된 값으로 JSON을 반환합니다."""
    
    if df.empty:
        return {"error": "No data to analyze."}

    # --- 데이터 전처리 ---
    df['거래금액_num'] = to_numeric(get_col_from_df(df, '거래금액', 'dealAmount'))
    df['전용면적_num'] = to_numeric(get_col_from_df(df, '전용면적', 'area', 'excluUseAr', 'buildingAr'))
    df['건축년도_num'] = to_numeric(get_col_from_df(df, '건축년도', 'buildYear'))
    
    df.dropna(subset=['거래금액_num', '전용면적_num'], inplace=True)
    df = df[df['전용면적_num'] > 0].copy()
    if df.empty:
        return {"error": "No valid transaction data after cleaning."}

    df['평당가_만원'] = (df['거래금액_num'] / df['전용면적_num']) * 3.305785
    
    current_year = datetime.now().year
    df['건물연령'] = current_year - df['건축년도_num']

    # --- Formatting helpers ---
    def krw_10k(v): return format_unit(v, "만원")
    def krw_10k_per_pyeong(v): return format_unit(v, "만원/평")

    # --- 1. 종합 통계 (Overall Statistics) ---
    total_count = len(df)
    total_value = df['거래금액_num'].sum()
    property_type_col = get_col_from_df(df, '주용도', '유형', 'buildingUse')
    type_distribution = property_type_col.value_counts().to_dict() if property_type_col.notna().any() else {}

    overall_stats = {
        "totalTransactionCount": total_count,
        "totalTransactionValue": krw_10k(total_value),
        "transactionDistributionByPropertyType": type_distribution
    }

    # --- 2. 가격 수준 통계 (Price Level Statistics) ---
    price_stats_raw = df['거래금액_num'].agg(['mean', 'median', 'max', 'min'])
    price_stats = {
        "overallAveragePrice": krw_10k(price_stats_raw['mean']),
        "overallMedianPrice": krw_10k(price_stats_raw['median']),
        "overallHighestPrice": krw_10k(price_stats_raw['max']),
        "overallLowestPrice": krw_10k(price_stats_raw['min'])
    }
    
    price_stats["representativeDeals"] = {
        "highestPriceDeal": clean_deal_for_display(df.loc[df['거래금액_num'].idxmax()]),
        "lowestPriceDeal": clean_deal_for_display(df.loc[df['거래금액_num'].idxmin()]),
        "dealClosestToAverage": clean_deal_for_display(df.loc[(df['거래금액_num'] - price_stats_raw['mean']).abs().idxmin()]),
        "dealClosestToMedian": clean_deal_for_display(df.loc[(df['거래금액_num'] - price_stats_raw['median']).abs().idxmin()])
    }

    if property_type_col.notna().any():
        price_by_type_raw = df.groupby(property_type_col)['거래금액_num'].agg(['mean', 'median', 'max', 'min'])
        price_stats["priceStatisticsByPropertyType"] = {
            prop_type: {
                "averagePrice": krw_10k(stats['mean']),
                "medianPrice": krw_10k(stats['median']),
                "highestPrice": krw_10k(stats['max']),
                "lowestPrice": krw_10k(stats['min']),
            } for prop_type, stats in price_by_type_raw.to_dict('index').items()
        }

    # --- 3. 단위 면적당 가격 통계 (Price per Area Statistics) ---
    price_per_area_stats_raw = df['평당가_만원'].agg(['mean', 'median'])
    price_per_area_stats = {
        "overallAveragePricePerPyeong": krw_10k_per_pyeong(price_per_area_stats_raw['mean']),
        "overallMedianPricePerPyeong": krw_10k_per_pyeong(price_per_area_stats_raw['median']),
    }
    if property_type_col.notna().any():
        price_per_area_by_type_raw = df.groupby(property_type_col)['평당가_만원'].agg(['mean', 'median'])
        price_per_area_stats["pricePerPyeongStatisticsByPropertyType"] = {
            prop_type: {
                "averagePricePerPyeong": krw_10k_per_pyeong(stats['mean']),
                "medianPricePerPyeong": krw_10k_per_pyeong(stats['median']),
            } for prop_type, stats in price_per_area_by_type_raw.to_dict('index').items()
        }

    # --- 4. 입지별 통계 (Location-based Statistics) ---
    location_col = get_col_from_df(df, '법정동', 'umdNm', 'dong')
    location_stats = {}
    if location_col.notna().any():
        location_summary_raw = df.groupby(location_col).agg(
            Count=('거래금액_num', 'size'),
            Mean_Price=('거래금액_num', 'mean'),
            Max_Price=('거래금액_num', 'max'),
            Min_Price=('거래금액_num', 'min'),
            Mean_PPA=('평당가_만원', 'mean'),
            Median_PPA=('평당가_만원', 'median')
        )
        
        for dong, stats in location_summary_raw.to_dict('index').items():
            location_stats[dong] = {
                "transactionCount": int(stats['Count']),
                "averagePrice": krw_10k(stats['Mean_Price']),
                "highestPrice": krw_10k(stats['Max_Price']),
                "lowestPrice": krw_10k(stats['Min_Price']),
                "averagePricePerPyeong": krw_10k_per_pyeong(stats['Mean_PPA']),
                "medianPricePerPyeong": krw_10k_per_pyeong(stats['Median_PPA']),
            }

    # --- 5. 건물 특성별 통계 (Building Characteristics Statistics) ---
    age_bins = [0, 6, 11, 21, np.inf]
    age_labels = ['5 years or newer', '6-10 years', '11-20 years', 'over 20 years']
    df['건물연령대'] = pd.cut(df['건물연령'], bins=age_bins, labels=age_labels, right=False)
    age_stats = {}
    if not df['건물연령대'].isnull().all():
        age_summary_raw = df.groupby('건물연령대', observed=True).agg(
            Count=('거래금액_num', 'size'),
            Mean_Price=('거래금액_num', 'mean'),
            Mean_PPA=('평당가_만원', 'mean')
        )
        age_stats = {
            age_group: {
                "transactionCount": int(stats['Count']),
                "averagePrice": krw_10k(stats['Mean_Price']),
                "averagePricePerPyeong": krw_10k_per_pyeong(stats['Mean_PPA']),
            } for age_group, stats in age_summary_raw.to_dict('index').items()
        }

    area_bins = [0, 100, 300, 1000, np.inf]
    area_labels = ['small (<100m²)', 'medium (100-300m²)', 'large (300-1000m²)', 'extra_large (>1000m²)']
    df['건물규모'] = pd.cut(df['전용면적_num'], bins=area_bins, labels=area_labels, right=False)
    scale_stats = {}
    if not df['건물규모'].isnull().all():
        scale_summary_raw = df.groupby('건물규모', observed=True).agg(
            Count=('거래금액_num', 'size'),
            Mean_Price=('거래금액_num', 'mean'),
            Mean_PPA=('평당가_만원', 'mean')
        )
        scale_stats = {
            scale_group: {
                "transactionCount": int(stats['Count']),
                "averagePrice": krw_10k(stats['Mean_Price']),
                "averagePricePerPyeong": krw_10k_per_pyeong(stats['Mean_PPA']),
            } for scale_group, stats in scale_summary_raw.to_dict('index').items()
        }
    
    building_stats = {
        "statisticsByBuildingAge": age_stats, 
        "statisticsByBuildingScale_exclusiveArea": scale_stats
    }

    return {
        "overallStatistics": overall_stats,
        "priceLevelStatistics": price_stats,
        "pricePerAreaStatistics": price_per_area_stats,
        "locationStatistics_byDong": location_stats,
        "buildingCharacteristicsStatistics": building_stats,
        "notes": "Price per pyeong and building scale are calculated based on the 'exclusive use area'. Data for 'land share' or 'road access conditions' is not provided by the API and is not included in this analysis."
    }

@mcp.tool(
    name="analyze_commercial_property_trade",
    description="""상업업무용(오피스, 상가) 부동산 매매 실거래 데이터 파일을 분석하여 월간 리포트 형식의 핵심 통계 요약을 제공합니다.
이 도구는 `get_commercial_property_trade_data`를 통해 얻은 데이터 파일의 경로를 입력받아 작동합니다.
종합 통계, 가격 수준, 평당가, 입지, 건물 특성별 등 다각적인 분석 결과를 반환합니다.
분석 결과를 바탕으로, 주요 통계 지표들을 사용자가 이해하기 쉽도록 차트나 그래프로 시각화하여 리포트를 작성해 주세요.

Arguments:
- file_path (str, required): `get_commercial_property_trade_data` 도구로 생성된 `raw.data.json` 데이터 파일의 경로.

Returns:
- 통계 분석 결과가 담긴 상세한 JSON 문자열.
""",
    tags={"통계", "분석", "리포트", "상업업무용", "실거래가"}
)
def analyze_commercial_property_trade(file_path: str, ctx: Optional[Any] = None) -> TextContent:
    """
    상업업무용 부동산 거래 데이터 XML 파일을 분석하여 통계 요약을 생성합니다.
    """
    def call(context):
        try:
            p = Path(file_path)
            if not p.exists():
                return json.dumps({"error": f"파일을 찾을 수 없습니다: {file_path}"}, ensure_ascii=False)

            cache_path = get_summary_cache_path(p, property_type="commercial")

            # 캐시 확인 및 재사용 로직
            if cache_path.exists():
                source_mtime = p.stat().st_mtime
                cache_mtime = cache_path.stat().st_mtime
                if cache_mtime > source_mtime:
                    logger.info(f"✅ 유효한 캐시를 사용합니다: {cache_path}")
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        return f.read()
            
            logger.info(f"🔄 캐시가 없거나 오래되어 새로운 분석을 수행합니다: {file_path}")
            df = pd.read_json(p, lines=True)
            
            summary_data = analyze_commercial_property_data(df)
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=4, default=default_serializer)

            summary_data["summary_cached_path"] = str(cache_path)
            
            return json.dumps(summary_data, ensure_ascii=False, indent=4, default=default_serializer)

        except Exception as e:
            logger.error(f"상업업무용 부동산 데이터 분석 중 오류 발생: {e}", exc_info=True)
            return json.dumps({"error": f"분석 중 오류가 발생했습니다: {str(e)}"}, ensure_ascii=False)
            
    result = with_context(ctx, "analyze_commercial_property_trade", call)
    return TextContent(type="text", text=result)

# --- 아파트 매매 분석 ---

def analyze_apartment_trade_data(df: pd.DataFrame) -> Dict[str, Any]:
    """DataFrame을 받아 아파트 매매 통계를 분석하고 영문 key와 단위가 포함된 값으로 JSON을 반환합니다."""
    if df.empty:
        return {"error": "No data to analyze."}

    # --- 데이터 전처리 ---
    df['거래금액_num'] = to_numeric(get_col_from_df(df, '거래금액', 'dealAmount'))
    df['전용면적_num'] = to_numeric(get_col_from_df(df, '전용면적', 'area', 'excluUseAr'))
    df['건축년도_num'] = to_numeric(get_col_from_df(df, '건축년도', 'buildYear'))
    df['계약년월_num'] = to_numeric(get_col_from_df(df, '계약년월'))
    df['계약일_num'] = to_numeric(get_col_from_df(df, '계약일'))

    df.dropna(subset=['거래금액_num', '전용면적_num'], inplace=True)
    df = df[df['전용면적_num'] > 0].copy()
    if df.empty:
        return {"error": "No valid transaction data after cleaning."}

    df['평당가_만원'] = (df['거래금액_num'] / df['전용면적_num']) * 3.305785
    current_year = datetime.now().year
    df['건물연령'] = current_year - df['건축년도_num']

    def krw_10k(v): return format_unit(v, "만원")
    def krw_10k_per_pyeong(v): return format_unit(v, "만원/평")

    # --- 1. 종합 통계 ---
    total_count = len(df)
    total_value = df['거래금액_num'].sum()
    overall_stats = {
        "totalTransactionCount": total_count,
        "totalTransactionValue": krw_10k(total_value),
    }

    # --- 2. 가격 수준 통계 ---
    price_stats_raw = df['거래금액_num'].agg(['mean', 'median', 'max', 'min'])
    price_stats = {
        "overallAveragePrice": krw_10k(price_stats_raw['mean']),
        "overallMedianPrice": krw_10k(price_stats_raw['median']),
        "overallHighestPrice": krw_10k(price_stats_raw['max']),
        "overallLowestPrice": krw_10k(price_stats_raw['min']),
        "representativeDeals": {
            "highestPriceDeal": clean_deal_for_display(df.loc[df['거래금액_num'].idxmax()]),
            "lowestPriceDeal": clean_deal_for_display(df.loc[df['거래금액_num'].idxmin()]),
            "dealClosestToAverage": clean_deal_for_display(df.loc[(df['거래금액_num'] - price_stats_raw['mean']).abs().idxmin()]),
            "dealClosestToMedian": clean_deal_for_display(df.loc[(df['거래금액_num'] - price_stats_raw['median']).abs().idxmin()])
        }
    }

    # --- 3. 단위 면적당 가격 통계 ---
    price_per_area_stats = {
        "overallAveragePricePerPyeong": krw_10k_per_pyeong(df['평당가_만원'].mean()),
        "overallMedianPricePerPyeong": krw_10k_per_pyeong(df['평당가_만원'].median()),
    }

    # --- 4. 단지별/입지별 통계 ---
    complex_col = get_col_from_df(df, '아파트', '단지명', 'aptName')
    location_col = get_col_from_df(df, '법정동', 'umdNm', 'dong')
    
    def get_grouped_stats(group_col):
        stats = {}
        if group_col.notna().any():
            summary_raw = df.groupby(group_col).agg(
                Count=('거래금액_num', 'size'),
                Mean_Price=('거래금액_num', 'mean'),
                Median_Price=('거래금액_num', 'median'),
                Mean_PPA=('평당가_만원', 'mean'),
                Median_PPA=('평당가_만원', 'median')
            )
            for name, data in summary_raw.to_dict('index').items():
                stats[name] = {
                    "transactionCount": int(data['Count']),
                    "averagePrice": krw_10k(data['Mean_Price']),
                    "medianPrice": krw_10k(data['Median_Price']),
                    "averagePricePerPyeong": krw_10k_per_pyeong(data['Mean_PPA']),
                    "medianPricePerPyeong": krw_10k_per_pyeong(data['Median_PPA']),
                }
        return stats

    complex_stats = get_grouped_stats(complex_col)
    location_stats = get_grouped_stats(location_col)

    return {
        "overallStatistics": overall_stats,
        "priceLevelStatistics": price_stats,
        "pricePerAreaStatistics": price_per_area_stats,
        "statisticsByApartmentComplex": complex_stats,
        "statisticsByDong": location_stats,
        "notes": "PPA (Price Per Pyeong) is calculated based on the 'exclusive use area'."
    }

@mcp.tool(
    name="analyze_apartment_trade",
    description="""아파트 매매 실거래 데이터 파일을 분석하여 월간 리포트 형식의 핵심 통계 요약을 제공합니다.
이 도구는 `get_apt_trade_data`를 통해 얻은 데이터 파일의 경로를 입력받아 작동합니다.
종합 통계, 가격 수준, 평당가, 단지별, 동별 등 다각적인 분석 결과를 반환합니다.
분석 결과를 바탕으로, 주요 통계 지표들을 사용자가 이해하기 쉽도록 차트나 그래프로 시각화하여 리포트를 작성해 주세요.

Arguments:
- file_path (str, required): `get_apt_trade_data` 도구로 생성된 `raw.data.json` 데이터 파일의 경로.

Returns:
- 통계 분석 결과가 담긴 상세한 JSON 문자열.
""",
    tags={"아파트", "통계", "분석", "리포트", "매매", "실거래가"}
)
def analyze_apartment_trade(file_path: str, ctx: Optional[Any] = None) -> TextContent:
    """
    아파트 매매 거래 데이터 XML 파일을 분석하여 통계 요약을 생성합니다.
    """
    def call(context):
        try:
            p = Path(file_path)
            if not p.exists():
                return json.dumps({"error": f"파일을 찾을 수 없습니다: {file_path}"}, ensure_ascii=False)

            cache_path = get_summary_cache_path(p, property_type="apartment", trade_type="trade")

            if cache_path.exists():
                if cache_path.stat().st_mtime > p.stat().st_mtime:
                    logger.info(f"✅ 유효한 아파트 매매 캐시를 사용합니다: {cache_path}")
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        return f.read()
            
            logger.info(f"🔄 새로운 아파트 매매 분석을 수행합니다: {file_path}")
            df = pd.read_json(p, lines=True)
            
            summary_data = analyze_apartment_trade_data(df)
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=4, default=default_serializer)

            summary_data["summary_cached_path"] = str(cache_path)
            return json.dumps(summary_data, ensure_ascii=False, indent=4, default=default_serializer)

        except Exception as e:
            logger.error(f"아파트 매매 데이터 분석 중 오류 발생: {e}", exc_info=True)
            return json.dumps({"error": f"분석 중 오류가 발생했습니다: {str(e)}"}, ensure_ascii=False)
            
    result = with_context(ctx, "analyze_apartment_trade", call)
    return TextContent(type="text", text=result)

# --- 아파트 전월세 분석 ---

def analyze_apartment_rent_data(df: pd.DataFrame) -> Dict[str, Any]:
    """DataFrame을 받아 아파트 전월세 통계를 분석하고 전세/월세를 구분하여 JSON으로 반환합니다."""
    if df.empty:
        return {"error": "No data to analyze."}

    # --- 데이터 전처리 ---
    df['보증금_num'] = to_numeric(get_col_from_df(df, '보증금액', '보증금', 'deposit', 'depositNum'))
    df['월세_num'] = to_numeric(get_col_from_df(df, '월세액', '월세', 'monthlyRent', 'rentFeeNum'))
    df['전용면적_num'] = to_numeric(get_col_from_df(df, '전용면적', 'area', 'excluUseAr', 'areaNum'))
    df['건축년도_num'] = to_numeric(get_col_from_df(df, '건축년도', 'buildYear'))
    df['계약년월_num'] = to_numeric(get_col_from_df(df, '계약년월'))
    df['계약일_num'] = to_numeric(get_col_from_df(df, '계약일'))

    df.dropna(subset=['보증금_num', '월세_num', '전용면적_num'], inplace=True)
    df = df[df['전용면적_num'] > 0].copy()
    if df.empty:
        return {"error": "No valid transaction data after cleaning."}

    df_jeonse = df[df['월세_num'] == 0].copy()
    df_wolse = df[df['월세_num'] > 0].copy()

    def krw_10k(v): return format_unit(v, "만원")
    
    def analyze_rent_type(df_rent_type, rent_type_name):
        if df_rent_type.empty:
            return { "totalTransactionCount": 0 }

        stats = { "totalTransactionCount": len(df_rent_type) }
        
        price_stats_raw = df_rent_type['보증금_num'].agg(['mean', 'median', 'max', 'min'])
        stats['depositPriceStatistics'] = {
            "averageDeposit": krw_10k(price_stats_raw['mean']),
            "medianDeposit": krw_10k(price_stats_raw['median']),
            "highestDeposit": krw_10k(price_stats_raw['max']),
            "lowestDeposit": krw_10k(price_stats_raw['min']),
            "representativeDeals": {
                "highestDepositDeal": clean_deal_for_display(df_rent_type.loc[df_rent_type['보증금_num'].idxmax()]),
                "lowestDepositDeal": clean_deal_for_display(df_rent_type.loc[df_rent_type['보증금_num'].idxmin()]),
            }
        }
        if rent_type_name == 'wolse': # 월세 통계 추가
            wolse_stats_raw = df_rent_type['월세_num'].agg(['mean', 'median', 'max', 'min'])
            stats['monthlyRentStatistics'] = {
                "averageMonthlyRent": krw_10k(wolse_stats_raw['mean']),
                "medianMonthlyRent": krw_10k(wolse_stats_raw['median']),
            }

        complex_col = get_col_from_df(df_rent_type, '아파트', '단지명', 'aptName')
        if complex_col.notna().any():
            stats['statisticsByApartmentComplex'] = df_rent_type.groupby(complex_col).agg(
                transactionCount=('보증금_num', 'size'),
                averageDeposit=('보증금_num', 'mean')
            ).apply(lambda x: x.astype(int) if x.name == 'transactionCount' else krw_10k(x)).to_dict('index')

        return stats

    jeonse_analysis = analyze_rent_type(df_jeonse, 'jeonse')
    wolse_analysis = analyze_rent_type(df_wolse, 'wolse')
    
    return {
        "transactionTypeDistribution": {
            "jeonse_count": len(df_jeonse),
            "wolse_count": len(df_wolse),
        },
        "jeonseAnalysis": jeonse_analysis,
        "wolseAnalysis": wolse_analysis,
        "notes": "Statistics are separated by transaction type (Jeonse vs. Wolse)."
    }

@mcp.tool(
    name="analyze_apartment_rent",
    description="""아파트 전월세 실거래 데이터 파일을 분석하여 월간 리포트 형식의 핵심 통계 요약을 제공합니다.
이 도구는 `get_apt_rent_data`를 통해 얻은 데이터 파일의 경로를 입력받아 작동하며, '전세'와 '월세'를 자동으로 구분하여 각각에 대한 상세 통계를 제공합니다.
분석 결과를 바탕으로, 주요 통계 지표들을 사용자가 이해하기 쉽도록 차트나 그래프로 시각화하여 리포트를 작성해 주세요.

- **거래 유형 분포**: 전체 거래 중 전세와 월세의 비중을 보여줍니다.
- **전세 분석**: 보증금에 대한 평균/중위/최고/최저 가격 및 주요 거래 사례를 제공합니다. 단지별 통계도 포함됩니다.
- **월세 분석**: 보증금 및 월세 각각에 대한 평균/중위 가격 통계를 제공합니다. 단지별 통계도 포함됩니다.

Arguments:
- file_path (str, required): `get_apt_rent_data` 도구로 생성된 `raw.data.json` 데이터 파일의 경로.

Returns:
- 전세와 월세로 구분된 통계 분석 결과가 담긴 상세한 JSON 문자열.
""",
    tags={"아파트", "통계", "분석", "리포트", "전세", "월세", "전월세", "실거래가"}
)
def analyze_apartment_rent(file_path: str, ctx: Optional[Any] = None) -> TextContent:
    """
    아파트 전월세 거래 데이터 XML 파일을 분석하여 통계 요약을 생성합니다.
    """
    def call(context):
        try:
            p = Path(file_path)
            if not p.exists():
                return json.dumps({"error": f"파일을 찾을 수 없습니다: {file_path}"}, ensure_ascii=False)

            cache_path = get_summary_cache_path(p, property_type="apartment", trade_type="rent")

            if cache_path.exists():
                if cache_path.stat().st_mtime > p.stat().st_mtime:
                    logger.info(f"✅ 유효한 아파트 전월세 캐시를 사용합니다: {cache_path}")
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        return f.read()
            
            logger.info(f"🔄 새로운 아파트 전월세 분석을 수행합니다: {file_path}")
            df = pd.read_json(p, lines=True)
            
            summary_data = analyze_apartment_rent_data(df)
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=4, default=default_serializer)

            summary_data["summary_cached_path"] = str(cache_path)
            return json.dumps(summary_data, ensure_ascii=False, indent=4, default=default_serializer)

        except Exception as e:
            logger.error(f"아파트 전월세 데이터 분석 중 오류 발생: {e}", exc_info=True)
            return json.dumps({"error": f"분석 중 오류가 발생했습니다: {str(e)}"}, ensure_ascii=False)
            
    result = with_context(ctx, "analyze_apartment_rent", call)
    return TextContent(type="text", text=result)

# --- 오피스텔 매매 분석 ---

def analyze_officetel_trade_data(df: pd.DataFrame) -> Dict[str, Any]:
    """DataFrame을 받아 오피스텔 매매 통계를 분석하고 영문 key와 단위가 포함된 값으로 JSON을 반환합니다."""
    if df.empty:
        return {"error": "No data to analyze."}

    # --- 데이터 전처리 ---
    df['거래금액_num'] = to_numeric(get_col_from_df(df, '거래금액', 'dealAmount', 'dealAmountNum'))
    df['전용면적_num'] = to_numeric(get_col_from_df(df, '전용면적', 'area', 'excluUseAr', 'areaNum'))
    df['건축년도_num'] = to_numeric(get_col_from_df(df, '건축년도', 'buildYear', 'buildYearNum'))
    df['계약년월_num'] = to_numeric(get_col_from_df(df, '계약년월'))
    df['계약일_num'] = to_numeric(get_col_from_df(df, '계약일'))

    df.dropna(subset=['거래금액_num', '전용면적_num'], inplace=True)
    df = df[df['전용면적_num'] > 0].copy()
    if df.empty:
        return {"error": "No valid transaction data after cleaning."}

    df['평당가_만원'] = (df['거래금액_num'] / df['전용면적_num']) * 3.305785
    current_year = datetime.now().year
    df['건물연령'] = current_year - df['건축년도_num']

    def krw_10k(v): return format_unit(v, "만원")
    def krw_10k_per_pyeong(v): return format_unit(v, "만원/평")

    # --- 1. 종합 통계 ---
    total_count = len(df)
    total_value = df['거래금액_num'].sum()
    overall_stats = {
        "totalTransactionCount": total_count,
        "totalTransactionValue": krw_10k(total_value),
    }

    # --- 2. 가격 수준 통계 ---
    price_stats_raw = df['거래금액_num'].agg(['mean', 'median', 'max', 'min'])
    price_stats = {
        "overallAveragePrice": krw_10k(price_stats_raw['mean']),
        "overallMedianPrice": krw_10k(price_stats_raw['median']),
        "overallHighestPrice": krw_10k(price_stats_raw['max']),
        "overallLowestPrice": krw_10k(price_stats_raw['min']),
        "representativeDeals": {
            "highestPriceDeal": clean_deal_for_display(df.loc[df['거래금액_num'].idxmax()]),
            "lowestPriceDeal": clean_deal_for_display(df.loc[df['거래금액_num'].idxmin()]),
            "dealClosestToAverage": clean_deal_for_display(df.loc[(df['거래금액_num'] - price_stats_raw['mean']).abs().idxmin()]),
            "dealClosestToMedian": clean_deal_for_display(df.loc[(df['거래금액_num'] - price_stats_raw['median']).abs().idxmin()])
        }
    }

    # --- 3. 단위 면적당 가격 통계 ---
    price_per_area_stats = {
        "overallAveragePricePerPyeong": krw_10k_per_pyeong(df['평당가_만원'].mean()),
        "overallMedianPricePerPyeong": krw_10k_per_pyeong(df['평당가_만원'].median()),
    }

    # --- 4. 단지별/입지별 통계 ---
    complex_col = get_col_from_df(df, '오피스텔', '오피스텔명', 'officetelName')
    location_col = get_col_from_df(df, '법정동', 'umdNm', 'dong')
    def get_grouped_stats(group_col):
        stats = {}
        if group_col.notna().any():
            summary_raw = df.groupby(group_col).agg(
                Count=('거래금액_num', 'size'),
                Mean_Price=('거래금액_num', 'mean'),
                Median_Price=('거래금액_num', 'median'),
                Mean_PPA=('평당가_만원', 'mean'),
                Median_PPA=('평당가_만원', 'median')
            )
            for name, data in summary_raw.to_dict('index').items():
                stats[name] = {
                    "transactionCount": int(data['Count']),
                    "averagePrice": krw_10k(data['Mean_Price']),
                    "medianPrice": krw_10k(data['Median_Price']),
                    "averagePricePerPyeong": krw_10k_per_pyeong(data['Mean_PPA']),
                    "medianPricePerPyeong": krw_10k_per_pyeong(data['Median_PPA']),
                }
        return stats
    complex_stats = get_grouped_stats(complex_col)
    location_stats = get_grouped_stats(location_col)
    return {
        "overallStatistics": overall_stats,
        "priceLevelStatistics": price_stats,
        "pricePerAreaStatistics": price_per_area_stats,
        "statisticsByOfficetelComplex": complex_stats,
        "statisticsByDong": location_stats,
        "notes": "PPA (Price Per Pyeong) is calculated based on the 'exclusive use area'."
    }

@mcp.tool(
    name="analyze_officetel_trade",
    description="""오피스텔 매매 실거래 데이터 파일을 분석하여 월간 리포트 형식의 핵심 통계 요약을 제공합니다.\n이 도구는 `get_officetel_trade_data`를 통해 얻은 데이터 파일의 경로를 입력받아 작동합니다.\n종합 통계, 가격 수준, 평당가, 단지별, 동별 등 다각적인 분석 결과를 반환합니다.\n분석 결과를 바탕으로, 주요 통계 지표들을 사용자가 이해하기 쉽도록 차트나 그래프로 시각화하여 리포트를 작성해 주세요.\n\nArguments:\n- file_path (str, required): `get_officetel_trade_data` 도구로 생성된 `raw.data.json` 데이터 파일의 경로.\n\nReturns:\n- 통계 분석 결과가 담긴 상세한 JSON 문자열.""",
    tags={"오피스텔", "통계", "분석", "리포트", "매매", "실거래가"}
)
def analyze_officetel_trade(file_path: str, ctx: Optional[Any] = None) -> TextContent:
    def call(context):
        try:
            p = Path(file_path)
            if not p.exists():
                return json.dumps({"error": f"파일을 찾을 수 없습니다: {file_path}"}, ensure_ascii=False)
            cache_path = get_summary_cache_path(p, property_type="officetel", trade_type="trade")
            if cache_path.exists():
                if cache_path.stat().st_mtime > p.stat().st_mtime:
                    logger.info(f"✅ 유효한 오피스텔 매매 캐시를 사용합니다: {cache_path}")
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        return f.read()
            logger.info(f"🔄 새로운 오피스텔 매매 분석을 수행합니다: {file_path}")
            df = pd.read_json(p, lines=True)
            summary_data = analyze_officetel_trade_data(df)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=4, default=default_serializer)
            summary_data["summary_cached_path"] = str(cache_path)
            return json.dumps(summary_data, ensure_ascii=False, indent=4, default=default_serializer)
        except Exception as e:
            logger.error(f"오피스텔 매매 데이터 분석 중 오류 발생: {e}", exc_info=True)
            return json.dumps({"error": f"분석 중 오류가 발생했습니다: {str(e)}"}, ensure_ascii=False)
    result = with_context(ctx, "analyze_officetel_trade", call)
    return TextContent(type="text", text=result)

# --- 오피스텔 전월세 분석 ---
def analyze_officetel_rent_data(df: pd.DataFrame) -> Dict[str, Any]:
    """DataFrame을 받아 오피스텔 전월세 통계를 분석하고 전세/월세를 구분하여 JSON으로 반환합니다."""
    if df.empty:
        return {"error": "No data to analyze."}
    df['보증금_num'] = to_numeric(get_col_from_df(df, '보증금액', '보증금', 'deposit', 'depositNum'))
    df['월세_num'] = to_numeric(get_col_from_df(df, '월세금액', '월세', 'monthlyRent', 'rentFeeNum'))
    df['전용면적_num'] = to_numeric(get_col_from_df(df, '전용면적', 'area', 'excluUseAr', 'areaNum'))
    df['건축년도_num'] = to_numeric(get_col_from_df(df, '건축년도', 'buildYear', 'buildYearNum'))
    df['계약년월_num'] = to_numeric(get_col_from_df(df, '계약년월'))
    df['계약일_num'] = to_numeric(get_col_from_df(df, '계약일'))
    df.dropna(subset=['보증금_num', '월세_num', '전용면적_num'], inplace=True)
    df = df[df['전용면적_num'] > 0].copy()
    if df.empty:
        return {"error": "No valid transaction data after cleaning."}
    df_jeonse = df[df['월세_num'] == 0].copy()
    df_wolse = df[df['월세_num'] > 0].copy()
    def krw_10k(v): return format_unit(v, "만원")
    def analyze_rent_type(df_rent_type, rent_type_name):
        if df_rent_type.empty:
            return { "totalTransactionCount": 0 }
        stats = { "totalTransactionCount": len(df_rent_type) }
        price_stats_raw = df_rent_type['보증금_num'].agg(['mean', 'median', 'max', 'min'])
        stats['depositPriceStatistics'] = {
            "averageDeposit": krw_10k(price_stats_raw['mean']),
            "medianDeposit": krw_10k(price_stats_raw['median']),
            "highestDeposit": krw_10k(price_stats_raw['max']),
            "lowestDeposit": krw_10k(price_stats_raw['min']),
            "representativeDeals": {
                "highestDepositDeal": clean_deal_for_display(df_rent_type.loc[df_rent_type['보증금_num'].idxmax()]),
                "lowestDepositDeal": clean_deal_for_display(df_rent_type.loc[df_rent_type['보증금_num'].idxmin()]),
            }
        }
        if rent_type_name == 'wolse':
            wolse_stats_raw = df_rent_type['월세_num'].agg(['mean', 'median', 'max', 'min'])
            stats['monthlyRentStatistics'] = {
                "averageMonthlyRent": krw_10k(wolse_stats_raw['mean']),
                "medianMonthlyRent": krw_10k(wolse_stats_raw['median']),
            }
        complex_col = get_col_from_df(df_rent_type, '오피스텔', '오피스텔명', 'officetelName')
        if complex_col.notna().any():
            stats['statisticsByOfficetelComplex'] = df_rent_type.groupby(complex_col).agg(
                transactionCount=('보증금_num', 'size'),
                averageDeposit=('보증금_num', 'mean')
            ).apply(lambda x: x.astype(int) if x.name == 'transactionCount' else krw_10k(x)).to_dict('index')
        return stats
    jeonse_analysis = analyze_rent_type(df_jeonse, 'jeonse')
    wolse_analysis = analyze_rent_type(df_wolse, 'wolse')
    return {
        "transactionTypeDistribution": {
            "jeonse_count": len(df_jeonse),
            "wolse_count": len(df_wolse),
        },
        "jeonseAnalysis": jeonse_analysis,
        "wolseAnalysis": wolse_analysis,
        "notes": "Statistics are separated by transaction type (Jeonse vs. Wolse)."
    }

@mcp.tool(
    name="analyze_officetel_rent",
    description="""오피스텔 전월세 실거래 데이터 파일을 분석하여 월간 리포트 형식의 핵심 통계 요약을 제공합니다.\n이 도구는 `get_officetel_rent_data`를 통해 얻은 데이터 파일의 경로를 입력받아 작동하며, '전세'와 '월세'를 자동으로 구분하여 각각에 대한 상세 통계를 제공합니다.\n분석 결과를 바탕으로, 주요 통계 지표들을 사용자가 이해하기 쉽도록 차트나 그래프로 시각화하여 리포트를 작성해 주세요.\n\n- **거래 유형 분포**: 전체 거래 중 전세와 월세의 비중을 보여줍니다.\n- **전세 분석**: 보증금에 대한 평균/중위/최고/최저 가격 및 주요 거래 사례를 제공합니다. 단지별 통계도 포함됩니다.\n- **월세 분석**: 보증금 및 월세 각각에 대한 평균/중위 가격 통계를 제공합니다. 단지별 통계도 포함됩니다.\n\nArguments:\n- file_path (str, required): `get_officetel_rent_data` 도구로 생성된 `raw.data.json` 데이터 파일의 경로.\n\nReturns:\n- 전세와 월세로 구분된 통계 분석 결과가 담긴 상세한 JSON 문자열.""",
    tags={"오피스텔", "통계", "분석", "리포트", "전세", "월세", "전월세", "실거래가"}
)
def analyze_officetel_rent(file_path: str, ctx: Optional[Any] = None) -> TextContent:
    def call(context):
        try:
            p = Path(file_path)
            if not p.exists():
                return json.dumps({"error": f"파일을 찾을 수 없습니다: {file_path}"}, ensure_ascii=False)
            cache_path = get_summary_cache_path(p, property_type="officetel", trade_type="rent")
            if cache_path.exists():
                if cache_path.stat().st_mtime > p.stat().st_mtime:
                    logger.info(f"✅ 유효한 오피스텔 전월세 캐시를 사용합니다: {cache_path}")
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        return f.read()
            logger.info(f"🔄 새로운 오피스텔 전월세 분석을 수행합니다: {file_path}")
            df = pd.read_json(p, lines=True)
            summary_data = analyze_officetel_rent_data(df)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=4, default=default_serializer)
            summary_data["summary_cached_path"] = str(cache_path)
            return json.dumps(summary_data, ensure_ascii=False, indent=4, default=default_serializer)
        except Exception as e:
            logger.error(f"오피스텔 전월세 데이터 분석 중 오류 발생: {e}", exc_info=True)
            return json.dumps({"error": f"분석 중 오류가 발생했습니다: {str(e)}"}, ensure_ascii=False)
    result = with_context(ctx, "analyze_officetel_rent", call)
    return TextContent(type="text", text=result) 