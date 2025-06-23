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

def analyze_commercial_property_data(df: pd.DataFrame) -> Dict[str, Any]:
    """DataFrame을 받아 상업업무용 부동산 통계를 분석하고 영문 key와 단위가 포함된 값으로 JSON을 반환합니다."""
    
    if df.empty:
        return {"error": "No data to analyze."}

    def get_col_from_df(df_obj, *names):
        """Helper function to get column by trying multiple names."""
        for name in names:
            if name in df_obj.columns:
                return df_obj[name]
        return pd.Series(dtype='object', index=df_obj.index)

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
    description="""상업업무용 부동산(상가, 오피스 등) 매매 실거래 데이터 파일을 분석하여 월간 리포트 형식의 핵심 통계 요약을 제공합니다.
이 도구는 `get_commercial_property_trade_data`를 통해 얻은 데이터 파일의 경로를 입력받아 작동합니다.
종합 통계, 가격 수준, 평당가, 입지별, 건물 특성별 등 다각적인 분석 결과를 반환하여 시장 동향을 깊이 있게 파악할 수 있도록 돕습니다.
분석 결과를 바탕으로, 주요 통계 지표들을 사용자가 이해하기 쉽도록 차트나 그래프로 시각화하여 리포트를 작성해 주세요.

- **종합 통계**: 총 거래 건수, 총 거래 대금, 용도별 거래 분포(상가/판매, 업무시설 등)를 제공합니다.
- **가격 수준 통계**: 전체 및 용도별 평균/중위/최고/최저 거래가를 보여줍니다.
- **단위 면적당 가격 통계**: 전체 및 용도별 평균/중위 평당가를 제공하여 가치 비교 기준을 제시합니다.
- **입지별 통계**: 법정동별로 거래 건수와 평균 가격, 평당가 등을 분석하여 지역별 시장 편차를 보여줍니다.
- **건물 특성별 통계**: 건축 연령 및 건물 규모(전용면적 기준)에 따른 거래 분포와 평균 가격을 제공합니다.

Arguments:
- file_path (str, required): `get_commercial_property_trade_data` 도구로 생성된 XML 데이터 파일의 경로.

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

            cache_dir = p.parent.parent / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path = cache_dir / f"{p.stem}_summary.json"

            # 캐시 확인 및 재사용 로직
            if cache_path.exists():
                source_mtime = p.stat().st_mtime
                cache_mtime = cache_path.stat().st_mtime
                if cache_mtime > source_mtime:
                    logger.info(f"✅ 유효한 캐시를 사용합니다: {cache_path}")
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        return f.read()
            
            logger.info(f"🔄 캐시가 없거나 오래되어 새로운 분석을 수행합니다: {file_path}")
            tree = ET.parse(p)
            root = tree.getroot()
            
            all_items = root.findall('.//item')
            if not all_items:
                return json.dumps({"error": "XML 파일에 거래 데이터 아이템이 없습니다."}, ensure_ascii=False)
            
            records = [{child.tag: child.text for child in item} for item in all_items]
            df = pd.DataFrame(records)
            
            summary_data = analyze_commercial_property_data(df)
            
            def default_serializer(o):
                if isinstance(o, (np.integer, np.int64)): return int(o)
                if isinstance(o, (np.floating, np.float64)): return float(o)
                if isinstance(o, (np.ndarray)): return o.tolist()
                if isinstance(o, pd.Timestamp): return o.isoformat()
                raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=4, default=default_serializer)

            summary_data["summary_cached_path"] = str(cache_path)
            
            return json.dumps(summary_data, ensure_ascii=False, indent=4, default=default_serializer)

        except Exception as e:
            logger.error(f"상업업무용 부동산 데이터 분석 중 오류 발생: {e}", exc_info=True)
            return json.dumps({"error": f"분석 중 오류가 발생했습니다: {str(e)}"}, ensure_ascii=False)
            
    result = with_context(ctx, "analyze_commercial_property_trade", call)
    return TextContent(type="text", text=result) 