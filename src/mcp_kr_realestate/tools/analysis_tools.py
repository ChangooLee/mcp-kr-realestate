"""
부동산 데이터 분석 및 통계 리포팅 도구
"""

import logging
import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
from pathlib import Path
import json
from typing import Any, Optional, Dict, Annotated
from pydantic import Field
from datetime import datetime
import os
import re
import unicodedata
import glob
import time
from mcp_kr_realestate.apis.ecos_api import get_key_statistic_list

from mcp_kr_realestate.server import mcp
from mcp_kr_realestate.utils.ctx_helper import with_context
from mcp.types import TextContent
from mcp_kr_realestate.apis.reb_api import get_reb_stat_list, get_reb_stat_items, get_reb_stat_data, get_reb_stat_list_all, get_reb_stat_items_all, get_reb_stat_data_all, cache_stat_list_full, cache_stat_list
from mcp_kr_realestate.apis.ecos_api import (
    get_statistic_table_list,
    get_statistic_word,
    get_statistic_item_list,
    get_statistic_search,
    get_key_statistic_list,
)
from mcp_kr_realestate.utils.data_processor import get_cache_dir

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

def as_value_unit(value, unit_str, precision=0):
    if pd.isna(value):
        return None
    if unit_str == "만원":
        v = float(value) * 10000
        unit_str = "원"
    elif unit_str == "만원/평":
        v = float(value) * 10000
        unit_str = "원/평"
    else:
        if isinstance(value, (np.integer, int)):
            v = int(value)
        else:
            v = float(value)
    # 소수점 이하 버림 (정수 변환)
    v = int(v)
    return {"value": v, "unit": unit_str}

def clean_deal_for_display(series):
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
    # 숫자 필드 value/unit 구조로 변환
    for k in list(deal_dict.keys()):
        if k in ['dealAmount', 'dealAmountNum', '보증금', 'deposit', '보증금액', '월세', 'monthlyRent', '월세액', 'rentFee', 'rentFeeNum']:
            try:
                # Remove commas if it's a string, then convert to float
                if isinstance(deal_dict[k], str):
                    v = float(deal_dict[k].replace(',', '')) if deal_dict[k] is not None else None
                else:
                    v = float(deal_dict[k]) if deal_dict[k] is not None else None
            except Exception:
                continue
            deal_dict[k] = as_value_unit(v, "만원")
        elif k in ['평당가', '평당가_만원']:
            try:
                v = float(deal_dict[k]) if deal_dict[k] is not None else None
            except Exception:
                continue
            deal_dict[k] = as_value_unit(v, "만원/평")
        elif k in ['areaNum', '전용면적', 'excluUseAr', '계약면적', 'totalFloorAr', '연면적', 'YUA', 'plottageAr', 'landAr', 'dealArea', '계약면적_num', '전용면적_num', '연면적_num', '토지면적_num']:
            try:
                v = float(deal_dict[k]) if deal_dict[k] is not None else None
            except Exception:
                continue
            deal_dict[k] = as_value_unit(v, "㎡")
        elif k in ['건축년도', 'buildYear', 'buildYearNum']:
            try:
                v = float(deal_dict[k]) if deal_dict[k] is not None else None
            except Exception:
                continue
            deal_dict[k] = as_value_unit(v, "년")
        elif k in ['floor', 'floorNum']:
            try:
                v = float(deal_dict[k]) if deal_dict[k] is not None else None
            except Exception:
                continue
            deal_dict[k] = as_value_unit(v, "층")
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
    # Set cache directory to the correct path relative to project root
    cache_dir = Path(get_cache_dir())
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
    def as_value_unit_m(v): return as_value_unit(v, "만원")
    def as_value_unit_per_pyeong(v): return as_value_unit(v, "만원/평")

    # --- 1. 종합 통계 (Overall Statistics) ---
    total_count = len(df)
    total_value = df['거래금액_num'].sum()
    property_type_col = get_col_from_df(df, '주용도', '유형', 'buildingUse')
    type_distribution = property_type_col.value_counts().to_dict() if property_type_col.notna().any() else {}

    overall_stats = {
        "totalTransactionCount": total_count,
        "totalTransactionValue": as_value_unit_m(total_value),
        "transactionDistributionByPropertyType": type_distribution
    }

    # --- 2. 가격 수준 통계 (Price Level Statistics) ---
    price_stats_raw = df['거래금액_num'].agg(['mean', 'median', 'max', 'min'])
    price_stats = {
        "overallAveragePrice": as_value_unit_m(price_stats_raw['mean']),
        "overallMedianPrice": as_value_unit_m(price_stats_raw['median']),
        "overallHighestPrice": as_value_unit_m(price_stats_raw['max']),
        "overallLowestPrice": as_value_unit_m(price_stats_raw['min']),
        "representativeDeals": {
            "highestPriceDeal": clean_deal_for_display(df.loc[df['거래금액_num'].idxmax()]),
            "lowestPriceDeal": clean_deal_for_display(df.loc[df['거래금액_num'].idxmin()]),
            "dealClosestToAverage": clean_deal_for_display(df.loc[(df['거래금액_num'] - price_stats_raw['mean']).abs().idxmin()]),
            "dealClosestToMedian": clean_deal_for_display(df.loc[(df['거래금액_num'] - price_stats_raw['median']).abs().idxmin()])
        }
    }

    if property_type_col.notna().any():
        price_by_type_raw = df.groupby(property_type_col)['거래금액_num'].agg(['mean', 'median', 'max', 'min'])
        price_stats["priceStatisticsByPropertyType"] = {
            prop_type: {
                "averagePrice": as_value_unit_m(stats['mean']),
                "medianPrice": as_value_unit_m(stats['median']),
                "highestPrice": as_value_unit_m(stats['max']),
                "lowestPrice": as_value_unit_m(stats['min']),
            } for prop_type, stats in price_by_type_raw.to_dict('index').items()
        }

    # --- 3. 단위 면적당 가격 통계 (Price per Area Statistics) ---
    price_per_area_stats_raw = df['평당가_만원'].agg(['mean', 'median'])
    price_per_area_stats = {
        "overallAveragePricePerPyeong": as_value_unit_per_pyeong(price_per_area_stats_raw['mean']),
        "overallMedianPricePerPyeong": as_value_unit_per_pyeong(price_per_area_stats_raw['median']),
    }
    if property_type_col.notna().any():
        price_per_area_by_type_raw = df.groupby(property_type_col)['평당가_만원'].agg(['mean', 'median'])
        price_per_area_stats["pricePerPyeongStatisticsByPropertyType"] = {
            prop_type: {
                "averagePricePerPyeong": as_value_unit_per_pyeong(stats['mean']),
                "medianPricePerPyeong": as_value_unit_per_pyeong(stats['median']),
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
                "averagePrice": as_value_unit_m(stats['Mean_Price']),
                "highestPrice": as_value_unit_m(stats['Max_Price']),
                "lowestPrice": as_value_unit_m(stats['Min_Price']),
                "averagePricePerPyeong": as_value_unit_per_pyeong(stats['Mean_PPA']),
                "medianPricePerPyeong": as_value_unit_per_pyeong(stats['Median_PPA']),
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
                "averagePrice": as_value_unit_m(stats['Mean_Price']),
                "averagePricePerPyeong": as_value_unit_per_pyeong(stats['Mean_PPA']),
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
                "averagePrice": as_value_unit_m(stats['Mean_Price']),
                "averagePricePerPyeong": as_value_unit_per_pyeong(stats['Mean_PPA']),
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
def analyze_commercial_property_trade(
    file_path: Annotated[str, Field(description="분석할 raw.data.json 파일 경로")],
    ctx: Optional[Any] = None
) -> TextContent:
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

    def as_value_unit_m(v): return as_value_unit(v, "만원")
    def as_value_unit_per_pyeong(v): return as_value_unit(v, "만원/평")

    # --- 1. 종합 통계 ---
    total_count = len(df)
    total_value = df['거래금액_num'].sum()
    overall_stats = {
        "totalTransactionCount": total_count,
        "totalTransactionValue": as_value_unit_m(total_value),
    }

    # --- 2. 가격 수준 통계 ---
    price_stats_raw = df['거래금액_num'].agg(['mean', 'median', 'max', 'min'])
    price_stats = {
        "overallAveragePrice": as_value_unit_m(price_stats_raw['mean']),
        "overallMedianPrice": as_value_unit_m(price_stats_raw['median']),
        "overallHighestPrice": as_value_unit_m(price_stats_raw['max']),
        "overallLowestPrice": as_value_unit_m(price_stats_raw['min']),
        "representativeDeals": {
            "highestPriceDeal": clean_deal_for_display(df.loc[df['거래금액_num'].idxmax()]),
            "lowestPriceDeal": clean_deal_for_display(df.loc[df['거래금액_num'].idxmin()]),
            "dealClosestToAverage": clean_deal_for_display(df.loc[(df['거래금액_num'] - price_stats_raw['mean']).abs().idxmin()]),
            "dealClosestToMedian": clean_deal_for_display(df.loc[(df['거래금액_num'] - price_stats_raw['median']).abs().idxmin()])
        }
    }

    # --- 3. 단위 면적당 가격 통계 ---
    price_per_area_stats = {
        "overallAveragePricePerPyeong": as_value_unit_per_pyeong(df['평당가_만원'].mean()),
        "overallMedianPricePerPyeong": as_value_unit_per_pyeong(df['평당가_만원'].median()),
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
                    "averagePrice": as_value_unit_m(data['Mean_Price']),
                    "medianPrice": as_value_unit_m(data['Median_Price']),
                    "averagePricePerPyeong": as_value_unit_per_pyeong(data['Mean_PPA']),
                    "medianPricePerPyeong": as_value_unit_per_pyeong(data['Median_PPA']),
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
def analyze_apartment_trade(
    file_path: Annotated[str, Field(description="분석할 raw.data.json 파일 경로")],
    ctx: Optional[Any] = None
) -> TextContent:
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

    def as_value_unit_m(v): return as_value_unit(v, "만원")
    
    def analyze_rent_type(df_rent_type, rent_type_name):
        if df_rent_type.empty:
            return { "totalTransactionCount": 0 }

        stats = { "totalTransactionCount": len(df_rent_type) }
        
        price_stats_raw = df_rent_type['보증금_num'].agg(['mean', 'median', 'max', 'min'])
        stats['depositPriceStatistics'] = {
            "averageDeposit": as_value_unit_m(price_stats_raw['mean']),
            "medianDeposit": as_value_unit_m(price_stats_raw['median']),
            "highestDeposit": as_value_unit_m(price_stats_raw['max']),
            "lowestDeposit": as_value_unit_m(price_stats_raw['min']),
            "representativeDeals": {
                "highestDepositDeal": clean_deal_for_display(df_rent_type.loc[df_rent_type['보증금_num'].idxmax()]),
                "lowestDepositDeal": clean_deal_for_display(df_rent_type.loc[df_rent_type['보증금_num'].idxmin()]),
            }
        }
        if rent_type_name == 'wolse': # 월세 통계 추가
            wolse_stats_raw = df_rent_type['월세_num'].agg(['mean', 'median', 'max', 'min'])
            stats['monthlyRentStatistics'] = {
                "averageMonthlyRent": as_value_unit_m(wolse_stats_raw['mean']),
                "medianMonthlyRent": as_value_unit_m(wolse_stats_raw['median']),
            }

        complex_col = get_col_from_df(df_rent_type, '아파트', '단지명', 'aptName')
        if complex_col.notna().any():
            stats['statisticsByApartmentComplex'] = df_rent_type.groupby(complex_col).agg(
                transactionCount=('보증금_num', 'size'),
                averageDeposit=('보증금_num', 'mean')
            ).apply(lambda x: x.astype(int) if x.name == 'transactionCount' else as_value_unit_m(x)).to_dict('index')

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
    description="""아파트 전월세 실거래 데이터 파일을 분석하여 월간 리포트 형식의 핵심 통계 요약을 제공합니다.\n이 도구는 `get_apt_rent_data`를 통해 얻은 데이터 파일의 경로를 입력받아 작동하며, '전세'와 '월세'를 자동으로 구분하여 각각에 대한 상세 통계를 제공합니다.\n분석 결과를 바탕으로, 주요 통계 지표들을 사용자가 이해하기 쉽도록 차트나 그래프로 시각화하여 리포트를 작성해 주세요.\n\n- **거래 유형 분포**: 전체 거래 중 전세와 월세의 비중을 보여줍니다.\n- **전세 분석**: 보증금에 대한 평균/중위/최고/최저 가격 및 주요 거래 사례를 제공합니다. 단지별 통계도 포함됩니다.\n- **월세 분석**: 보증금 및 월세 각각에 대한 평균/중위 가격 통계를 제공합니다. 단지별 통계도 포함됩니다.\n\nArguments:\n- file_path (str, required): `get_apt_rent_data` 도구로 생성된 `raw.data.json` 데이터 파일의 경로.\n\nReturns:\n- 전세와 월세로 구분된 통계 분석 결과가 담긴 상세한 JSON 문자열.""",
    tags={"아파트", "통계", "분석", "리포트", "전세", "월세", "전월세", "실거래가"}
)
def analyze_apartment_rent(
    file_path: Annotated[str, Field(description="분석할 raw.data.json 파일 경로")],
    ctx: Optional[Any] = None
) -> TextContent:
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

    def as_value_unit_m(v): return as_value_unit(v, "만원")
    def as_value_unit_per_pyeong(v): return as_value_unit(v, "만원/평")

    # --- 1. 종합 통계 ---
    total_count = len(df)
    total_value = df['거래금액_num'].sum()
    overall_stats = {
        "totalTransactionCount": total_count,
        "totalTransactionValue": as_value_unit_m(total_value),
    }

    # --- 2. 가격 수준 통계 ---
    price_stats_raw = df['거래금액_num'].agg(['mean', 'median', 'max', 'min'])
    price_stats = {
        "overallAveragePrice": as_value_unit_m(price_stats_raw['mean']),
        "overallMedianPrice": as_value_unit_m(price_stats_raw['median']),
        "overallHighestPrice": as_value_unit_m(price_stats_raw['max']),
        "overallLowestPrice": as_value_unit_m(price_stats_raw['min']),
        "representativeDeals": {
            "highestPriceDeal": clean_deal_for_display(df.loc[df['거래금액_num'].idxmax()]),
            "lowestPriceDeal": clean_deal_for_display(df.loc[df['거래금액_num'].idxmin()]),
            "dealClosestToAverage": clean_deal_for_display(df.loc[(df['거래금액_num'] - price_stats_raw['mean']).abs().idxmin()]),
            "dealClosestToMedian": clean_deal_for_display(df.loc[(df['거래금액_num'] - price_stats_raw['median']).abs().idxmin()])
        }
    }

    # --- 3. 단위 면적당 가격 통계 ---
    price_per_area_stats = {
        "overallAveragePricePerPyeong": as_value_unit_per_pyeong(df['평당가_만원'].mean()),
        "overallMedianPricePerPyeong": as_value_unit_per_pyeong(df['평당가_만원'].median()),
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
                    "averagePrice": as_value_unit_m(data['Mean_Price']),
                    "medianPrice": as_value_unit_m(data['Median_Price']),
                    "averagePricePerPyeong": as_value_unit_per_pyeong(data['Mean_PPA']),
                    "medianPricePerPyeong": as_value_unit_per_pyeong(data['Median_PPA']),
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
def analyze_officetel_trade(
    file_path: Annotated[str, Field(description="분석할 raw.data.json 파일 경로")],
    ctx: Optional[Any] = None
) -> TextContent:
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
    df['월세_num'] = to_numeric(get_col_from_df(df, '월세액', '월세', 'monthlyRent', 'rentFeeNum'))
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
    def as_value_unit_m(v): return as_value_unit(v, "만원")
    def analyze_rent_type(df_rent_type, rent_type_name):
        if df_rent_type.empty:
            return { "totalTransactionCount": 0 }
        stats = { "totalTransactionCount": len(df_rent_type) }
        price_stats_raw = df_rent_type['보증금_num'].agg(['mean', 'median', 'max', 'min'])
        stats['depositPriceStatistics'] = {
            "averageDeposit": as_value_unit_m(price_stats_raw['mean']),
            "medianDeposit": as_value_unit_m(price_stats_raw['median']),
            "highestDeposit": as_value_unit_m(price_stats_raw['max']),
            "lowestDeposit": as_value_unit_m(price_stats_raw['min']),
            "representativeDeals": {
                "highestDepositDeal": clean_deal_for_display(df_rent_type.loc[df_rent_type['보증금_num'].idxmax()]),
                "lowestDepositDeal": clean_deal_for_display(df_rent_type.loc[df_rent_type['보증금_num'].idxmin()]),
            }
        }
        if rent_type_name == 'wolse':
            wolse_stats_raw = df_rent_type['월세_num'].agg(['mean', 'median', 'max', 'min'])
            stats['monthlyRentStatistics'] = {
                "averageMonthlyRent": as_value_unit_m(wolse_stats_raw['mean']),
                "medianMonthlyRent": as_value_unit_m(wolse_stats_raw['median']),
            }
        building_col = get_col_from_df(df_rent_type, '오피스텔', '오피스텔명', 'officetelName')
        if building_col.notna().any():
            stats['statisticsByOfficetelComplex'] = df_rent_type.groupby(building_col).agg(
                transactionCount=('보증금_num', 'size'),
                averageDeposit=('보증금_num', 'mean')
            ).apply(lambda x: x.astype(int) if x.name == 'transactionCount' else as_value_unit_m(x)).to_dict('index')
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
        "notes": "Statistics are separated by transaction type (Jeonse vs. Wolse). 계약면적 기준으로 집계합니다."
    }

@mcp.tool(
    name="analyze_officetel_rent",
    description="""오피스텔 전월세 실거래 데이터 파일을 분석하여 월간 리포트 형식의 핵심 통계 요약을 제공합니다.\n이 도구는 `get_officetel_rent_data`를 통해 얻은 데이터 파일의 경로를 입력받아 작동하며, '전세'와 '월세'를 자동으로 구분하여 각각에 대한 상세 통계를 제공합니다.\n분석 결과를 바탕으로, 주요 통계 지표들을 사용자가 이해하기 쉽도록 차트나 그래프로 시각화하여 리포트를 작성해 주세요.\n\n- **거래 유형 분포**: 전체 거래 중 전세와 월세의 비중을 보여줍니다.\n- **전세 분석**: 보증금에 대한 평균/중위/최고/최저 가격 및 주요 거래 사례를 제공합니다. 건물명별 통계도 포함됩니다.\n- **월세 분석**: 보증금 및 월세 각각에 대한 평균/중위 가격 통계를 제공합니다. 건물명별 통계도 포함됩니다.\n\nArguments:\n- file_path (str, required): `get_officetel_rent_data` 도구로 생성된 `raw.data.json` 데이터 파일의 경로.\n\nReturns:\n- 전세와 월세로 구분된 통계 분석 결과가 담긴 상세한 JSON 문자열.""",
    tags={"오피스텔", "통계", "분석", "리포트", "전세", "월세", "전월세", "실거래가"}
)
def analyze_officetel_rent(
    file_path: Annotated[str, Field(description="분석할 raw.data.json 파일 경로")],
    ctx: Optional[Any] = None
) -> TextContent:
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

def analyze_single_detached_trade_data(df: pd.DataFrame) -> Dict[str, Any]:
    """DataFrame을 받아 단독/다가구 매매 통계를 분석하고 영문 key와 단위가 포함된 값으로 JSON을 반환합니다."""
    if df.empty:
        return {"error": "No data to analyze."}
    # --- 데이터 전처리 ---
    df['거래금액_num'] = to_numeric(get_col_from_df(df, '거래금액', 'dealAmount', 'dealAmountNum'))
    # Fix: Use totalFloorAr if areaNum/YUA are null
    df['연면적_num'] = to_numeric(get_col_from_df(df, '연면적', 'YUA', 'totalFloorAr', 'areaNum'))
    df['건축년도_num'] = to_numeric(get_col_from_df(df, '건축년도', 'buildYear', 'buildYearNum'))
    df['계약년월_num'] = to_numeric(get_col_from_df(df, '계약년월'))
    df['계약일_num'] = to_numeric(get_col_from_df(df, '계약일'))
    df.dropna(subset=['거래금액_num', '연면적_num'], inplace=True)
    df = df[df['연면적_num'] > 0].copy()
    if df.empty:
        return {"error": "No valid transaction data after cleaning."}
    df['평당가_만원'] = (df['거래금액_num'] / df['연면적_num']) * 3.305785
    current_year = datetime.now().year
    df['건물연령'] = current_year - df['건축년도_num']
    def as_value_unit_m(v): return as_value_unit(v, "만원")
    def as_value_unit_per_pyeong(v): return as_value_unit(v, "만원/평")
    # --- 1. 종합 통계 ---
    total_count = len(df)
    total_value = df['거래금액_num'].sum()
    overall_stats = {
        "totalTransactionCount": total_count,
        "totalTransactionValue": as_value_unit_m(total_value),
    }
    # --- 2. 가격 수준 통계 ---
    price_stats_raw = df['거래금액_num'].agg(['mean', 'median', 'max', 'min'])
    price_stats = {
        "overallAveragePrice": as_value_unit_m(price_stats_raw['mean']),
        "overallMedianPrice": as_value_unit_m(price_stats_raw['median']),
        "overallHighestPrice": as_value_unit_m(price_stats_raw['max']),
        "overallLowestPrice": as_value_unit_m(price_stats_raw['min']),
        "representativeDeals": {
            "highestPriceDeal": clean_deal_for_display(df.loc[df['거래금액_num'].idxmax()]),
            "lowestPriceDeal": clean_deal_for_display(df.loc[df['거래금액_num'].idxmin()]),
            "dealClosestToAverage": clean_deal_for_display(df.loc[(df['거래금액_num'] - price_stats_raw['mean']).abs().idxmin()]),
            "dealClosestToMedian": clean_deal_for_display(df.loc[(df['거래금액_num'] - price_stats_raw['median']).abs().idxmin()])
        }
    }
    # --- 3. 단위 면적당 가격 통계 ---
    price_per_area_stats = {
        "overallAveragePricePerPyeong": as_value_unit_per_pyeong(df['평당가_만원'].mean()),
        "overallMedianPricePerPyeong": as_value_unit_per_pyeong(df['평당가_만원'].median()),
    }
    # --- 4. 건물명/동별 통계 ---
    building_col = get_col_from_df(df, '건물명', 'buildingName')
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
                    "averagePrice": as_value_unit_m(data['Mean_Price']),
                    "medianPrice": as_value_unit_m(data['Median_Price']),
                    "averagePricePerPyeong": as_value_unit_per_pyeong(data['Mean_PPA']),
                    "medianPricePerPyeong": as_value_unit_per_pyeong(data['Median_PPA']),
                }
        return stats
    building_stats = get_grouped_stats(building_col)
    location_stats = get_grouped_stats(location_col)
    return {
        "overallStatistics": overall_stats,
        "priceLevelStatistics": price_stats,
        "pricePerAreaStatistics": price_per_area_stats,
        "statisticsByBuilding": building_stats,
        "statisticsByDong": location_stats,
        "notes": "PPA (Price Per Pyeong) is calculated based on the 'gross floor area'. 단독/다가구는 연면적(totalFloorAr) 기준으로 집계합니다."
    }

@mcp.tool(
    name="analyze_single_detached_house_trade",
    description="""단독/다가구 매매 실거래 데이터 파일을 분석하여 월간 리포트 형식의 핵심 통계 요약을 제공합니다.\n이 도구는 `get_single_detached_house_trade_data`를 통해 얻은 데이터 파일의 경로를 입력받아 작동합니다.\n종합 통계, 가격 수준, 평당가, 건물명별, 동별 등 다각적인 분석 결과를 반환합니다.\n분석 결과를 바탕으로, 주요 통계 지표들을 사용자가 이해하기 쉽도록 차트나 그래프로 시각화하여 리포트를 작성해 주세요.\n\nArguments:\n- file_path (str, required): `get_single_detached_house_trade_data` 도구로 생성된 `raw.data.json` 데이터 파일의 경로.\n\nReturns:\n- 통계 분석 결과가 담긴 상세한 JSON 문자열.""",
    tags={"단독다가구", "통계", "분석", "리포트", "매매", "실거래가"}
)
def analyze_single_detached_house_trade(
    file_path: Annotated[str, Field(description="분석할 raw.data.json 파일 경로")],
    ctx: Optional[Any] = None
) -> TextContent:
    def call(context):
        try:
            p = Path(file_path)
            if not p.exists():
                return json.dumps({"error": f"파일을 찾을 수 없습니다: {file_path}"}, ensure_ascii=False)
            cache_path = get_summary_cache_path(p, property_type="single_detached", trade_type="trade")
            if cache_path.exists():
                if cache_path.stat().st_mtime > p.stat().st_mtime:
                    logger.info(f"✅ 유효한 단독/다가구 매매 캐시를 사용합니다: {cache_path}")
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        return f.read()
            logger.info(f"🔄 새로운 단독/다가구 매매 분석을 수행합니다: {file_path}")
            df = pd.read_json(p, lines=True)
            summary_data = analyze_single_detached_trade_data(df)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=4, default=default_serializer)
            summary_data["summary_cached_path"] = str(cache_path)
            return json.dumps(summary_data, ensure_ascii=False, indent=4, default=default_serializer)
        except Exception as e:
            logger.error(f"단독/다가구 매매 데이터 분석 중 오류 발생: {e}", exc_info=True)
            return json.dumps({"error": f"분석 중 오류가 발생했습니다: {str(e)}"}, ensure_ascii=False)
    result = with_context(ctx, "analyze_single_detached_house_trade", call)
    return TextContent(type="text", text=result)

# --- 단독/다가구 전월세 분석 ---
def analyze_single_detached_rent_data(df: pd.DataFrame) -> Dict[str, Any]:
    """DataFrame을 받아 단독/다가구 전월세 통계를 분석하고 전세/월세를 구분하여 JSON으로 반환합니다."""
    if df.empty:
        return {"error": "No data to analyze."}
    df['보증금_num'] = to_numeric(get_col_from_df(df, '보증금액', '보증금', 'deposit', 'depositNum'))
    df['월세_num'] = to_numeric(get_col_from_df(df, '월세액', '월세', 'monthlyRent', 'rentFeeNum'))
    df['계약면적_num'] = to_numeric(get_col_from_df(df, '계약면적', 'contractArea', 'areaNum'))
    df['건축년도_num'] = to_numeric(get_col_from_df(df, '건축년도', 'buildYear', 'buildYearNum'))
    df['계약년월_num'] = to_numeric(get_col_from_df(df, '계약년월'))
    df['계약일_num'] = to_numeric(get_col_from_df(df, '계약일'))
    df.dropna(subset=['보증금_num', '월세_num', '계약면적_num'], inplace=True)
    df = df[df['계약면적_num'] > 0].copy()
    if df.empty:
        return {"error": "No valid transaction data after cleaning."}
    df_jeonse = df[df['월세_num'] == 0].copy()
    df_wolse = df[df['월세_num'] > 0].copy()
    def as_value_unit_m(v): return as_value_unit(v, "만원")
    def analyze_rent_type(df_rent_type, rent_type_name):
        if df_rent_type.empty:
            return { "totalTransactionCount": 0 }
        stats = { "totalTransactionCount": len(df_rent_type) }
        price_stats_raw = df_rent_type['보증금_num'].agg(['mean', 'median', 'max', 'min'])
        stats['depositPriceStatistics'] = {
            "averageDeposit": as_value_unit_m(price_stats_raw['mean']),
            "medianDeposit": as_value_unit_m(price_stats_raw['median']),
            "highestDeposit": as_value_unit_m(price_stats_raw['max']),
            "lowestDeposit": as_value_unit_m(price_stats_raw['min']),
            "representativeDeals": {
                "highestDepositDeal": clean_deal_for_display(df_rent_type.loc[df_rent_type['보증금_num'].idxmax()]),
                "lowestDepositDeal": clean_deal_for_display(df_rent_type.loc[df_rent_type['보증금_num'].idxmin()]),
            }
        }
        if rent_type_name == 'wolse':
            wolse_stats_raw = df_rent_type['월세_num'].agg(['mean', 'median', 'max', 'min'])
            stats['monthlyRentStatistics'] = {
                "averageMonthlyRent": as_value_unit_m(wolse_stats_raw['mean']),
                "medianMonthlyRent": as_value_unit_m(wolse_stats_raw['median']),
            }
        building_col = get_col_from_df(df_rent_type, '건물명', 'buildingName')
        if building_col.notna().any():
            stats['statisticsByBuilding'] = df_rent_type.groupby(building_col).agg(
                transactionCount=('보증금_num', 'size'),
                averageDeposit=('보증금_num', 'mean')
            ).apply(lambda x: x.astype(int) if x.name == 'transactionCount' else as_value_unit_m(x)).to_dict('index')
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
        "notes": "Statistics are separated by transaction type (Jeonse vs. Wolse). 계약면적 기준으로 집계합니다."
    }

@mcp.tool(
    name="analyze_single_detached_house_rent",
    description="""단독/다가구 전월세 실거래 데이터 파일을 분석하여 월간 리포트 형식의 핵심 통계 요약을 제공합니다.\n이 도구는 `get_sh_rent_data`를 통해 얻은 데이터 파일의 경로를 입력받아 작동하며, '전세'와 '월세'를 자동으로 구분하여 각각에 대한 상세 통계를 제공합니다.\n분석 결과를 바탕으로, 주요 통계 지표들을 사용자가 이해하기 쉽도록 차트나 그래프로 시각화하여 리포트를 작성해 주세요.\n\n- **거래 유형 분포**: 전체 거래 중 전세와 월세의 비중을 보여줍니다.\n- **전세 분석**: 보증금에 대한 평균/중위/최고/최저 가격 및 주요 거래 사례를 제공합니다. 건물명별 통계도 포함됩니다.\n- **월세 분석**: 보증금 및 월세 각각에 대한 평균/중위 가격 통계를 제공합니다. 건물명별 통계도 포함됩니다.\n\nArguments:\n- file_path (str, required): `get_sh_rent_data` 도구로 생성된 `raw.data.json` 데이터 파일의 경로.\n\nReturns:\n- 전세와 월세로 구분된 통계 분석 결과가 담긴 상세한 JSON 문자열.""",
    tags={"단독다가구", "통계", "분석", "리포트", "전세", "월세", "전월세", "실거래가"}
)
def analyze_single_detached_house_rent(
    file_path: Annotated[str, Field(description="분석할 raw.data.json 파일 경로")],
    ctx: Optional[Any] = None
) -> TextContent:
    def call(context):
        try:
            p = Path(file_path)
            if not p.exists():
                return json.dumps({"error": f"파일을 찾을 수 없습니다: {file_path}"}, ensure_ascii=False)
            cache_path = get_summary_cache_path(p, property_type="single_detached", trade_type="rent")
            if cache_path.exists():
                if cache_path.stat().st_mtime > p.stat().st_mtime:
                    logger.info(f"✅ 유효한 단독/다가구 전월세 캐시를 사용합니다: {cache_path}")
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        return f.read()
            logger.info(f"🔄 새로운 단독/다가구 전월세 분석을 수행합니다: {file_path}")
            df = pd.read_json(p, lines=True)
            summary_data = analyze_single_detached_rent_data(df)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=4, default=default_serializer)
            summary_data["summary_cached_path"] = str(cache_path)
            return json.dumps(summary_data, ensure_ascii=False, indent=4, default=default_serializer)
        except Exception as e:
            logger.error(f"단독/다가구 전월세 데이터 분석 중 오류 발생: {e}", exc_info=True)
            return json.dumps({"error": f"분석 중 오류가 발생했습니다: {str(e)}"}, ensure_ascii=False)
    result = with_context(ctx, "analyze_single_detached_house_rent", call)
    return TextContent(type="text", text=result)

def analyze_row_house_trade_data(df: pd.DataFrame) -> Dict[str, Any]:
    """DataFrame을 받아 연립다세대 매매 통계를 분석하고 영문 key와 단위가 포함된 값으로 JSON을 반환합니다."""
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
    def as_value_unit_m(v): return as_value_unit(v, "만원")
    def as_value_unit_per_pyeong(v): return as_value_unit(v, "만원/평")
    # --- 1. 종합 통계 ---
    total_count = len(df)
    total_value = df['거래금액_num'].sum()
    overall_stats = {
        "totalTransactionCount": total_count,
        "totalTransactionValue": as_value_unit_m(total_value),
    }
    # --- 2. 가격 수준 통계 ---
    price_stats_raw = df['거래금액_num'].agg(['mean', 'median', 'max', 'min'])
    price_stats = {
        "overallAveragePrice": as_value_unit_m(price_stats_raw['mean']),
        "overallMedianPrice": as_value_unit_m(price_stats_raw['median']),
        "overallHighestPrice": as_value_unit_m(price_stats_raw['max']),
        "overallLowestPrice": as_value_unit_m(price_stats_raw['min']),
        "representativeDeals": {
            "highestPriceDeal": clean_deal_for_display(df.loc[df['거래금액_num'].idxmax()]),
            "lowestPriceDeal": clean_deal_for_display(df.loc[df['거래금액_num'].idxmin()]),
            "dealClosestToAverage": clean_deal_for_display(df.loc[(df['거래금액_num'] - price_stats_raw['mean']).abs().idxmin()]),
            "dealClosestToMedian": clean_deal_for_display(df.loc[(df['거래금액_num'] - price_stats_raw['median']).abs().idxmin()])
        }
    }
    # --- 3. 단위 면적당 가격 통계 ---
    price_per_area_stats = {
        "overallAveragePricePerPyeong": as_value_unit_per_pyeong(df['평당가_만원'].mean()),
        "overallMedianPricePerPyeong": as_value_unit_per_pyeong(df['평당가_만원'].median()),
    }
    # --- 4. 연립다세대명/동별 통계 ---
    building_col = get_col_from_df(df, '연립다세대명', 'rowHouseName')
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
                    "averagePrice": as_value_unit_m(data['Mean_Price']),
                    "medianPrice": as_value_unit_m(data['Median_Price']),
                    "averagePricePerPyeong": as_value_unit_per_pyeong(data['Mean_PPA']),
                    "medianPricePerPyeong": as_value_unit_per_pyeong(data['Median_PPA']),
                }
        return stats
    building_stats = get_grouped_stats(building_col)
    location_stats = get_grouped_stats(location_col)
    return {
        "overallStatistics": overall_stats,
        "priceLevelStatistics": price_stats,
        "pricePerAreaStatistics": price_per_area_stats,
        "statisticsByRowHouseComplex": building_stats,
        "statisticsByDong": location_stats,
        "notes": "PPA (Price Per Pyeong) is calculated based on the 'exclusive use area'. 연립다세대는 단지명(연립다세대명) 기준 집계가 가능하며, 단지명이 없으면 동별로 집계합니다."
    }

@mcp.tool(
    name="analyze_row_house_trade",
    description="""연립다세대 매매 실거래 데이터 파일을 분석하여 월간 리포트 형식의 핵심 통계 요약을 제공합니다.\n이 도구는 `get_row_house_trade_data`를 통해 얻은 데이터 파일의 경로를 입력받아 작동합니다.\n종합 통계, 가격 수준, 평당가, 단지별, 동별 등 다각적인 분석 결과를 반환합니다.\n분석 결과를 바탕으로, 주요 통계 지표들을 사용자가 이해하기 쉽도록 차트나 그래프로 시각화하여 리포트를 작성해 주세요.\n\nArguments:\n- file_path (str, required): `get_row_house_trade_data` 도구로 생성된 `raw.data.json` 데이터 파일의 경로.\n\nReturns:\n- 통계 분석 결과가 담긴 상세한 JSON 문자열.""",
    tags={"연립다세대", "통계", "분석", "리포트", "매매", "실거래가"}
)
def analyze_row_house_trade(
    file_path: Annotated[str, Field(description="분석할 raw.data.json 파일 경로")],
    ctx: Optional[Any] = None
) -> TextContent:
    def call(context):
        try:
            p = Path(file_path)
            if not p.exists():
                return json.dumps({"error": f"파일을 찾을 수 없습니다: {file_path}"}, ensure_ascii=False)
            cache_path = get_summary_cache_path(p, property_type="row_house", trade_type="trade")
            if cache_path.exists():
                if cache_path.stat().st_mtime > p.stat().st_mtime:
                    logger.info(f"✅ 유효한 연립다세대 매매 캐시를 사용합니다: {cache_path}")
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        return f.read()
            logger.info(f"🔄 새로운 연립다세대 매매 분석을 수행합니다: {file_path}")
            df = pd.read_json(p, lines=True)
            summary_data = analyze_row_house_trade_data(df)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=4, default=default_serializer)
            summary_data["summary_cached_path"] = str(cache_path)
            return json.dumps(summary_data, ensure_ascii=False, indent=4, default=default_serializer)
        except Exception as e:
            logger.error(f"연립다세대 매매 데이터 분석 중 오류 발생: {e}", exc_info=True)
            return json.dumps({"error": f"분석 중 오류가 발생했습니다: {str(e)}"}, ensure_ascii=False)
    result = with_context(ctx, "analyze_row_house_trade", call)
    return TextContent(type="text", text=result)

def analyze_row_house_rent_data(df: pd.DataFrame) -> Dict[str, Any]:
    """DataFrame을 받아 연립다세대 전월세 통계를 분석하고 전세/월세를 구분하여 JSON으로 반환합니다."""
    if df.empty:
        return {"error": "No data to analyze."}
    df['보증금_num'] = to_numeric(get_col_from_df(df, '보증금액', '보증금', 'deposit', 'depositNum'))
    df['월세_num'] = to_numeric(get_col_from_df(df, '월세액', '월세', 'monthlyRent', 'rentFeeNum'))
    # Fix: Use excluUseAr as fallback for area, before areaNum
    df['계약면적_num'] = to_numeric(get_col_from_df(df, '계약면적', 'contractArea', 'excluUseAr', 'areaNum'))
    df['건축년도_num'] = to_numeric(get_col_from_df(df, '건축년도', 'buildYear', 'buildYearNum'))
    df['계약년월_num'] = to_numeric(get_col_from_df(df, '계약년월'))
    df['계약일_num'] = to_numeric(get_col_from_df(df, '계약일'))
    df.dropna(subset=['보증금_num', '월세_num', '계약면적_num'], inplace=True)
    df = df[df['계약면적_num'] > 0].copy()
    if df.empty:
        return {"error": "No valid transaction data after cleaning."}
    df_jeonse = df[df['월세_num'] == 0].copy()
    df_wolse = df[df['월세_num'] > 0].copy()
    def as_value_unit_m(v): return as_value_unit(v, "만원")
    def analyze_rent_type(df_rent_type, rent_type_name):
        if df_rent_type.empty:
            return { "totalTransactionCount": 0 }
        stats = { "totalTransactionCount": len(df_rent_type) }
        price_stats_raw = df_rent_type['보증금_num'].agg(['mean', 'median', 'max', 'min'])
        stats['depositPriceStatistics'] = {
            "averageDeposit": as_value_unit_m(price_stats_raw['mean']),
            "medianDeposit": as_value_unit_m(price_stats_raw['median']),
            "highestDeposit": as_value_unit_m(price_stats_raw['max']),
            "lowestDeposit": as_value_unit_m(price_stats_raw['min']),
            "representativeDeals": {
                "highestDepositDeal": clean_deal_for_display(df_rent_type.loc[df_rent_type['보증금_num'].idxmax()]),
                "lowestDepositDeal": clean_deal_for_display(df_rent_type.loc[df_rent_type['보증금_num'].idxmin()]),
            }
        }
        if rent_type_name == 'wolse':
            wolse_stats_raw = df_rent_type['월세_num'].agg(['mean', 'median', 'max', 'min'])
            stats['monthlyRentStatistics'] = {
                "averageMonthlyRent": as_value_unit_m(wolse_stats_raw['mean']),
                "medianMonthlyRent": as_value_unit_m(wolse_stats_raw['median']),
            }
        building_col = get_col_from_df(df_rent_type, '연립다세대명', 'rowHouseName')
        if building_col.notna().any():
            stats['statisticsByRowHouseComplex'] = df_rent_type.groupby(building_col).agg(
                transactionCount=('보증금_num', 'size'),
                averageDeposit=('보증금_num', 'mean')
            ).apply(lambda x: x.astype(int) if x.name == 'transactionCount' else as_value_unit_m(x)).to_dict('index')
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
        "notes": "Statistics are separated by transaction type (Jeonse vs. Wolse). 계약면적 기준으로 집계합니다. (excluUseAr도 자동 활용)"
    }

@mcp.tool(
    name="analyze_row_house_rent",
    description="""연립다세대 전월세 실거래 데이터 파일을 분석하여 월간 리포트 형식의 핵심 통계 요약을 제공합니다.\n이 도구는 `get_row_house_rent_data`를 통해 얻은 데이터 파일의 경로를 입력받아 작동하며, '전세'와 '월세'를 자동으로 구분하여 각각에 대한 상세 통계를 제공합니다.\n분석 결과를 바탕으로, 주요 통계 지표들을 사용자가 이해하기 쉽도록 차트나 그래프로 시각화하여 리포트를 작성해 주세요.\n\n- **거래 유형 분포**: 전체 거래 중 전세와 월세의 비중을 보여줍니다.\n- **전세 분석**: 보증금에 대한 평균/중위/최고/최저 가격 및 주요 거래 사례를 제공합니다. 건물명별 통계도 포함됩니다.\n- **월세 분석**: 보증금 및 월세 각각에 대한 평균/중위 가격 통계를 제공합니다. 건물명별 통계도 포함됩니다.\n\nArguments:\n- file_path (str, required): `get_row_house_rent_data` 도구로 생성된 `raw.data.json` 데이터 파일의 경로.\n\nReturns:\n- 전세와 월세로 구분된 통계 분석 결과가 담긴 상세한 JSON 문자열.""",
    tags={"연립다세대", "통계", "분석", "리포트", "전세", "월세", "전월세", "실거래가"}
)
def analyze_row_house_rent(
    file_path: Annotated[str, Field(description="분석할 raw.data.json 파일 경로")],
    ctx: Optional[Any] = None
) -> TextContent:
    def call(context):
        try:
            p = Path(file_path)
            if not p.exists():
                return json.dumps({"error": f"파일을 찾을 수 없습니다: {file_path}"}, ensure_ascii=False)
            cache_path = get_summary_cache_path(p, property_type="row_house", trade_type="rent")
            if cache_path.exists():
                if cache_path.stat().st_mtime > p.stat().st_mtime:
                    logger.info(f"✅ 유효한 연립다세대 전월세 캐시를 사용합니다: {cache_path}")
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        return f.read()
            logger.info(f"🔄 새로운 연립다세대 전월세 분석을 수행합니다: {file_path}")
            df = pd.read_json(p, lines=True)
            summary_data = analyze_row_house_rent_data(df)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=4, default=default_serializer)
            summary_data["summary_cached_path"] = str(cache_path)
            return json.dumps(summary_data, ensure_ascii=False, indent=4, default=default_serializer)
        except Exception as e:
            logger.error(f"연립다세대 전월세 데이터 분석 중 오류 발생: {e}", exc_info=True)
            return json.dumps({"error": f"분석 중 오류가 발생했습니다: {str(e)}"}, ensure_ascii=False)
    result = with_context(ctx, "analyze_row_house_rent", call)
    return TextContent(type="text", text=result)

def analyze_industrial_property_data(df: pd.DataFrame) -> Dict[str, Any]:
    """DataFrame을 받아 공장/창고 등 산업용 부동산 통계를 분석하고 영문 key와 단위가 포함된 값으로 JSON을 반환합니다."""
    if df.empty:
        return {"error": "No data to analyze."}
    # --- 데이터 전처리 ---
    df['거래금액_num'] = to_numeric(get_col_from_df(df, '거래금액', 'dealAmount', 'dealAmountNum'))
    # Fix: include 'buildingAr' as a fallback for area
    df['전용면적_num'] = to_numeric(get_col_from_df(df, '전용면적', 'area', 'excluUseAr', 'buildingAr', 'areaNum'))
    df['건축년도_num'] = to_numeric(get_col_from_df(df, '건축년도', 'buildYear', 'buildYearNum'))
    df.dropna(subset=['거래금액_num', '전용면적_num'], inplace=True)
    df = df[df['전용면적_num'] > 0].copy()
    if df.empty:
        return {"error": "No valid transaction data after cleaning."}
    df['평당가_만원'] = (df['거래금액_num'] / df['전용면적_num']) * 3.305785
    current_year = datetime.now().year
    df['건물연령'] = current_year - df['건축년도_num']
    def as_value_unit_m(v): return as_value_unit(v, "만원")
    def as_value_unit_per_pyeong(v): return as_value_unit(v, "만원/평")
    # --- 1. 종합 통계 ---
    total_count = len(df)
    total_value = df['거래금액_num'].sum()
    use_col = get_col_from_df(df, '용도', '유형', 'buildingUse')
    use_distribution = use_col.value_counts().to_dict() if use_col.notna().any() else {}
    overall_stats = {
        "totalTransactionCount": total_count,
        "totalTransactionValue": as_value_unit_m(total_value),
        "transactionDistributionByUseType": use_distribution
    }
    # --- 2. 가격 수준 통계 ---
    price_stats_raw = df['거래금액_num'].agg(['mean', 'median', 'max', 'min'])
    price_stats = {
        "overallAveragePrice": as_value_unit_m(price_stats_raw['mean']),
        "overallMedianPrice": as_value_unit_m(price_stats_raw['median']),
        "overallHighestPrice": as_value_unit_m(price_stats_raw['max']),
        "overallLowestPrice": as_value_unit_m(price_stats_raw['min']),
        "representativeDeals": {
            "highestPriceDeal": clean_deal_for_display(df.loc[df['거래금액_num'].idxmax()]),
            "lowestPriceDeal": clean_deal_for_display(df.loc[df['거래금액_num'].idxmin()]),
            "dealClosestToAverage": clean_deal_for_display(df.loc[(df['거래금액_num'] - price_stats_raw['mean']).abs().idxmin()]),
            "dealClosestToMedian": clean_deal_for_display(df.loc[(df['거래금액_num'] - price_stats_raw['median']).abs().idxmin()])
        }
    }
    # --- 3. 단위 면적당 가격 통계 ---
    price_per_area_stats = {
        "overallAveragePricePerPyeong": as_value_unit_per_pyeong(df['평당가_만원'].mean()),
        "overallMedianPricePerPyeong": as_value_unit_per_pyeong(df['평당가_만원'].median()),
    }
    if use_col.notna().any():
        price_by_use_raw = df.groupby(use_col)['거래금액_num'].agg(['mean', 'median', 'max', 'min'])
        price_stats["priceStatisticsByUseType"] = {
            use: {
                "averagePrice": as_value_unit_m(stats['mean']),
                "medianPrice": as_value_unit_m(stats['median']),
                "highestPrice": as_value_unit_m(stats['max']),
                "lowestPrice": as_value_unit_m(stats['min']),
            } for use, stats in price_by_use_raw.to_dict('index').items()
        }
        price_per_area_by_use_raw = df.groupby(use_col)['평당가_만원'].agg(['mean', 'median'])
        price_per_area_stats["pricePerPyeongStatisticsByUseType"] = {
            use: {
                "averagePricePerPyeong": as_value_unit_per_pyeong(stats['mean']),
                "medianPricePerPyeong": as_value_unit_per_pyeong(stats['median']),
            } for use, stats in price_per_area_by_use_raw.to_dict('index').items()
        }
    # --- 4. 입지별 통계 (동별) ---
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
                "averagePrice": as_value_unit_m(stats['Mean_Price']),
                "highestPrice": as_value_unit_m(stats['Max_Price']),
                "lowestPrice": as_value_unit_m(stats['Min_Price']),
                "averagePricePerPyeong": as_value_unit_per_pyeong(stats['Mean_PPA']),
                "medianPricePerPyeong": as_value_unit_per_pyeong(stats['Median_PPA']),
            }
    # --- 5. 건물 특성별 통계 (연령/규모) ---
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
                "averagePrice": as_value_unit_m(stats['Mean_Price']),
                "averagePricePerPyeong": as_value_unit_per_pyeong(stats['Mean_PPA']),
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
                "averagePrice": as_value_unit_m(stats['Mean_Price']),
                "averagePricePerPyeong": as_value_unit_per_pyeong(stats['Mean_PPA']),
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
        "statisticsByUseType": price_stats.get("priceStatisticsByUseType", {}),
        "locationStatistics_byDong": location_stats,
        "buildingCharacteristicsStatistics": building_stats,
        "notes": "공장/창고 등 산업용 부동산은 용도(공장/창고/기타), 전용면적, 건물연령, 층고, 대지/건물면적 등 특성이 중요합니다. 평당가는 전용면적 기준입니다."
    }

@mcp.tool(
    name="analyze_industrial_property_trade",
    description="""공장/창고 등 산업용 부동산 매매 실거래 데이터 파일을 분석하여 월간 리포트 형식의 핵심 통계 요약을 제공합니다.\n이 도구는 `get_indu_trade_data`를 통해 얻은 데이터 파일의 경로를 입력받아 작동합니다.\n종합 통계, 가격 수준, 평당가, 용도별, 동별, 건물 특성별 등 다각적인 분석 결과를 반환합니다.\n분석 결과를 바탕으로, 주요 통계 지표들을 사용자가 이해하기 쉽도록 차트나 그래프로 시각화하여 리포트를 작성해 주세요.\n\nArguments:\n- file_path (str, required): `get_indu_trade_data` 도구로 생성된 `raw.data.json` 데이터 파일의 경로.\n\nReturns:\n- 통계 분석 결과가 담긴 상세한 JSON 문자열.""",
    tags={"공장", "창고", "산업용", "통계", "분석", "리포트", "매매", "실거래가"}
)
def analyze_industrial_property_trade(
    file_path: Annotated[str, Field(description="분석할 raw.data.json 파일 경로")],
    ctx: Optional[Any] = None
) -> TextContent:
    def call(context):
        try:
            p = Path(file_path)
            if not p.exists():
                return json.dumps({"error": f"파일을 찾을 수 없습니다: {file_path}"}, ensure_ascii=False)
            cache_path = get_summary_cache_path(p, property_type="industrial", trade_type=None)
            if cache_path.exists():
                if cache_path.stat().st_mtime > p.stat().st_mtime:
                    logger.info(f"✅ 유효한 산업용 부동산 매매 캐시를 사용합니다: {cache_path}")
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        return f.read()
            logger.info(f"🔄 새로운 산업용 부동산 매매 분석을 수행합니다: {file_path}")
            df = pd.read_json(p, lines=True)
            summary_data = analyze_industrial_property_data(df)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=4, default=default_serializer)
            summary_data["summary_cached_path"] = str(cache_path)
            return json.dumps(summary_data, ensure_ascii=False, indent=4, default=default_serializer)
        except Exception as e:
            logger.error(f"산업용 부동산 매매 데이터 분석 중 오류 발생: {e}", exc_info=True)
            return json.dumps({"error": f"분석 중 오류가 발생했습니다: {str(e)}"}, ensure_ascii=False)
    result = with_context(ctx, "analyze_industrial_property_trade", call)
    return TextContent(type="text", text=result) 

def analyze_land_property_data(df: pd.DataFrame) -> Dict[str, Any]:
    """DataFrame을 받아 토지 매매 통계를 분석하고 영문 key와 단위가 포함된 값으로 JSON을 반환합니다."""
    if df.empty:
        return {"error": "No data to analyze."}
    # --- 데이터 전처리 ---
    df['거래금액_num'] = to_numeric(get_col_from_df(df, '거래금액', 'dealAmount', 'dealAmountNum'))
    # Fix: include 'dealArea' as a fallback for area
    df['토지면적_num'] = to_numeric(get_col_from_df(df, '면적', 'landAr', 'dealArea', 'area', 'areaNum'))
    df.dropna(subset=['거래금액_num', '토지면적_num'], inplace=True)
    df = df[df['토지면적_num'] > 0].copy()
    if df.empty:
        return {"error": "No valid transaction data after cleaning."}
    df['평당가_만원'] = (df['거래금액_num'] / df['토지면적_num']) * 3.305785
    def as_value_unit_m(v): return as_value_unit(v, "만원")
    def as_value_unit_per_pyeong(v): return as_value_unit(v, "만원/평")
    # --- 1. 종합 통계 ---
    total_count = len(df)
    total_value = df['거래금액_num'].sum()
    land_type_col = get_col_from_df(df, '지목', 'landType')
    type_distribution = land_type_col.value_counts().to_dict() if land_type_col.notna().any() else {}
    overall_stats = {
        "totalTransactionCount": total_count,
        "totalTransactionValue": as_value_unit_m(total_value),
        "transactionDistributionByLandType": type_distribution
    }
    # --- 2. 가격 수준 통계 ---
    price_stats_raw = df['거래금액_num'].agg(['mean', 'median', 'max', 'min'])
    price_stats = {
        "overallAveragePrice": as_value_unit_m(price_stats_raw['mean']),
        "overallMedianPrice": as_value_unit_m(price_stats_raw['median']),
        "overallHighestPrice": as_value_unit_m(price_stats_raw['max']),
        "overallLowestPrice": as_value_unit_m(price_stats_raw['min']),
        "representativeDeals": {
            "highestPriceDeal": clean_deal_for_display(df.loc[df['거래금액_num'].idxmax()]),
            "lowestPriceDeal": clean_deal_for_display(df.loc[df['거래금액_num'].idxmin()]),
            "dealClosestToAverage": clean_deal_for_display(df.loc[(df['거래금액_num'] - price_stats_raw['mean']).abs().idxmin()]),
            "dealClosestToMedian": clean_deal_for_display(df.loc[(df['거래금액_num'] - price_stats_raw['median']).abs().idxmin()])
        }
    }
    # --- 3. 단위 면적당 가격 통계 ---
    price_per_area_stats = {
        "overallAveragePricePerPyeong": as_value_unit_per_pyeong(df['평당가_만원'].mean()),
        "overallMedianPricePerPyeong": as_value_unit_per_pyeong(df['평당가_만원'].median()),
    }
    if land_type_col.notna().any():
        price_by_type_raw = df.groupby(land_type_col)['거래금액_num'].agg(['mean', 'median', 'max', 'min'])
        price_stats["priceStatisticsByLandType"] = {
            land_type: {
                "averagePrice": as_value_unit_m(stats['mean']),
                "medianPrice": as_value_unit_m(stats['median']),
                "highestPrice": as_value_unit_m(stats['max']),
                "lowestPrice": as_value_unit_m(stats['min']),
            } for land_type, stats in price_by_type_raw.to_dict('index').items()
        }
        price_per_area_by_type_raw = df.groupby(land_type_col)['평당가_만원'].agg(['mean', 'median'])
        price_per_area_stats["pricePerPyeongStatisticsByLandType"] = {
            land_type: {
                "averagePricePerPyeong": as_value_unit_per_pyeong(stats['mean']),
                "medianPricePerPyeong": as_value_unit_per_pyeong(stats['median']),
            } for land_type, stats in price_per_area_by_type_raw.to_dict('index').items()
        }
    # --- 4. 입지별 통계 (동별) ---
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
                "averagePrice": as_value_unit_m(stats['Mean_Price']),
                "highestPrice": as_value_unit_m(stats['Max_Price']),
                "lowestPrice": as_value_unit_m(stats['Min_Price']),
                "averagePricePerPyeong": as_value_unit_per_pyeong(stats['Mean_PPA']),
                "medianPricePerPyeong": as_value_unit_per_pyeong(stats['Median_PPA']),
            }
    return {
        "overallStatistics": overall_stats,
        "priceLevelStatistics": price_stats,
        "pricePerAreaStatistics": price_per_area_stats,
        "statisticsByLandType": price_stats.get("priceStatisticsByLandType", {}),
        "locationStatistics_byDong": location_stats,
        "notes": "토지 거래는 지목(용도), 면적, 도로접면, 형상, 방위 등 특성이 중요합니다. 평당가는 토지면적 기준입니다."
    }

@mcp.tool(
    name="analyze_land_trade",
    description="""토지 매매 실거래 데이터 파일을 분석하여 월간 리포트 형식의 핵심 통계 요약을 제공합니다.\n이 도구는 `get_land_trade_data`를 통해 얻은 데이터 파일의 경로를 입력받아 작동합니다.\n종합 통계, 가격 수준, 평당가, 지목별, 동별 등 다각적인 분석 결과를 반환합니다.\n분석 결과를 바탕으로, 주요 통계 지표들을 사용자가 이해하기 쉽도록 차트나 그래프로 시각화하여 리포트를 작성해 주세요.\n\nArguments:\n- file_path (str, required): `get_land_trade_data` 도구로 생성된 `raw.data.json` 데이터 파일의 경로.\n\nReturns:\n- 통계 분석 결과가 담긴 상세한 JSON 문자열.""",
    tags={"토지", "통계", "분석", "리포트", "매매", "실거래가"}
)
def analyze_land_trade(
    file_path: Annotated[str, Field(description="분석할 raw.data.json 파일 경로")],
    ctx: Optional[Any] = None
) -> TextContent:
    def call(context):
        try:
            p = Path(file_path)
            if not p.exists():
                return json.dumps({"error": f"파일을 찾을 수 없습니다: {file_path}"}, ensure_ascii=False)
            cache_path = get_summary_cache_path(p, property_type="land", trade_type=None)
            if cache_path.exists():
                if cache_path.stat().st_mtime > p.stat().st_mtime:
                    logger.info(f"✅ 유효한 토지 매매 캐시를 사용합니다: {cache_path}")
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        return f.read()
            logger.info(f"🔄 새로운 토지 매매 분석을 수행합니다: {file_path}")
            df = pd.read_json(p, lines=True)
            summary_data = analyze_land_property_data(df)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=4, default=default_serializer)
            summary_data["summary_cached_path"] = str(cache_path)
            return json.dumps(summary_data, ensure_ascii=False, indent=4, default=default_serializer)
        except Exception as e:
            logger.error(f"토지 매매 데이터 분석 중 오류 발생: {e}", exc_info=True)
            return json.dumps({"error": f"분석 중 오류가 발생했습니다: {str(e)}"}, ensure_ascii=False)
    result = with_context(ctx, "analyze_land_trade", call)
    return TextContent(type="text", text=result)

@mcp.tool(
    name="get_ecos_statistic_table_list",
    description="""
한국은행 ECOS 오픈API의 통계표 목록을 조회하고 캐싱합니다. (StatisticTableList)

사용법 예시:
get_ecos_statistic_table_list({"start": 1, "end": 100, "stat_code": null})
- start, end: 조회 시작/종료 인덱스(기본 1~100)
- stat_code: 특정 통계표코드로 필터링(선택)

결과는 json으로 캐싱되며, 캐시 파일 경로를 반환합니다.
""",
    tags={"ECOS", "통계", "목록", "한국은행"}
)
def get_ecos_statistic_table_list(
    params: Annotated[dict, Field(description="조회 파라미터 (start, end, stat_code)")]
) -> TextContent:
    path = get_statistic_table_list(params)
    return TextContent(type="text", text=str(path))

@mcp.tool(
    name="get_ecos_statistic_word",
    description="""
한국은행 ECOS 오픈API의 통계용어사전을 조회하고 캐싱합니다. (StatisticWord)

사용법 예시:
get_ecos_statistic_word({"word": null, "start": 1, "end": 100})
- word: 검색할 용어(선택)
- start, end: 조회 시작/종료 인덱스(기본 1~100)

결과는 json으로 캐싱되며, 캐시 파일 경로를 반환합니다.
""",
    tags={"ECOS", "통계", "용어", "사전", "한국은행"}
)
def get_ecos_statistic_word(
    params: Annotated[dict, Field(description="조회 파라미터 (word, start, end)")]
) -> TextContent:
    path = get_statistic_word(params)
    return TextContent(type="text", text=str(path))

@mcp.tool(
    name="get_ecos_statistic_item_list",
    description="""
한국은행 ECOS 오픈API의 통계 세부항목 목록을 조회하고 캐싱합니다. (StatisticItemList)

사용법 예시:
get_ecos_statistic_item_list({"stat_code": "601Y002", "start": 1, "end": 100})
- stat_code: 통계표코드(필수)
- start, end: 조회 시작/종료 인덱스(기본 1~100)

결과는 json으로 캐싱되며, 캐시 파일 경로를 반환합니다.
""",
    tags={"ECOS", "통계", "항목", "세부항목", "한국은행"}
)
def get_ecos_statistic_item_list(
    params: Annotated[dict, Field(description="조회 파라미터 (stat_code, start, end)")]
) -> TextContent:
    path = get_statistic_item_list(params)
    return TextContent(type="text", text=str(path))

@mcp.tool(
    name="get_ecos_statistic_search",
    description="""
한국은행 ECOS 오픈API의 통계 데이터를 조회하고 캐싱합니다. (StatisticSearch)

사용법 예시:
get_ecos_statistic_search({"stat_code": "200Y101", "cycle": "A", "start_time": "2020", "end_time": "2023", "item_code1": null, "item_code2": null, "item_code3": null, "item_code4": null, "start": 1, "end": 100})
- stat_code: 통계표코드(필수)
- cycle: 주기(A, S, Q, M, SM, D)
- start_time, end_time: 검색 시작/종료일자(주기에 맞는 형식)
- item_code1~4: 통계항목코드(선택)
- start, end: 조회 시작/종료 인덱스(기본 1~100)

결과는 json으로 캐싱되며, 캐시 파일 경로를 반환합니다.
""",
    tags={"ECOS", "통계", "조회", "데이터", "한국은행"}
)
def get_ecos_statistic_search(
    params: Annotated[dict, Field(description="조회 파라미터 (stat_code, cycle, start_time, end_time, item_codes)")]
) -> TextContent:
    from pathlib import Path
    import json
    path = get_statistic_search(params)
    cache_path = Path(path)
    if not cache_path.exists():
        return TextContent(type="text", text=json.dumps({"error": f"Cache file not found. Expected at: {str(cache_path)}"}, ensure_ascii=False, indent=2))
    return TextContent(type="text", text=str(cache_path))

@mcp.tool(
    name="get_ecos_key_statistic_list",
    description="""
한국은행 ECOS 오픈API의 100대 통계지표를 조회하고 캐싱합니다. (KeyStatisticList)

사용법 예시:
get_ecos_key_statistic_list({"start": 1, "end": 100})
- start, end: 조회 시작/종료 인덱스(기본 1~100)

결과는 json으로 캐싱되며, 캐시 파일 경로와 pandas 요약(preview, 상위 5개 주요 컬럼)을 반환합니다.
""",
    tags={"ECOS", "통계", "100대지표", "주요지표", "한국은행"}
)
def get_ecos_key_statistic_list(
    params: Annotated[dict, Field(description="조회 파라미터 (start, end)")]
) -> TextContent:
    path = get_key_statistic_list(params)
    if path is None:
        return TextContent(type="text", text=json.dumps({"error": "Cache path is None. Check your parameters."}, ensure_ascii=False, indent=2))
    try:
        with open(str(path), "r", encoding="utf-8") as f:
            data = json.load(f)
        # 실제 ECOS 응답 구조에 맞게 row 추출
        if "KeyStatisticList" in data and "row" in data["KeyStatisticList"]:
            rows = data["KeyStatisticList"]["row"]
            df = pd.DataFrame(rows)
            preview = df.head(5)[[c for c in df.columns if c in ["CLASS_NAME", "KEYSTAT_NAME", "DATA_VALUE", "CYCLE", "UNIT_NAME"] or c.lower().startswith("stat")]].to_dict(orient="records")
            return TextContent(type="text", text=json.dumps({"cache_path": str(path), "preview": preview}, ensure_ascii=False, indent=2))
        return TextContent(type="text", text=json.dumps({"cache_path": str(path), "preview": "No preview available"}, ensure_ascii=False, indent=2))
    except Exception as e:
        return TextContent(type="text", text=json.dumps({"cache_path": str(path), "error": str(e)}, ensure_ascii=False, indent=2))

def _normalize_korean(text):
    # 한글 자모 분리 및 소문자 변환
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize('NFKD', text)
    return ''.join([c for c in text if not unicodedata.combining(c)]).lower().replace(" ", "")

def _ecos_timerange_to_dates(cycle, timerange):
    """
    ECOS CYCLE: 'A'(연), 'M'(월), 'Q'(분기), 'D'(일)
    timerange: '2018-2024', '2020', '202301-202312', ...
    Returns: (start_time, end_time) in ECOS API format
    """
    import re
    import pandas as pd
    if not timerange:
        now = pd.Timestamp.now()
        if cycle == 'A':
            return str(now.year - 3), str(now.year)
        elif cycle == 'M':
            return (now - pd.DateOffset(years=3)).strftime('%Y%m'), now.strftime('%Y%m')
        elif cycle == 'Q':
            return f"{now.year-3}Q1", f"{now.year}Q4"
        elif cycle == 'D':
            return (now - pd.DateOffset(years=1)).strftime('%Y%m%d'), now.strftime('%Y%m%d')
        else:
            return str(now.year - 3), str(now.year)
    # timerange 파싱
    parts = re.split(r'[-~]', timerange)
    if len(parts) == 2:
        start, end = parts
    else:
        start = end = parts[0]
    # 각 주기별로 변환
    def pad(val, n):
        return val + '0'*(n-len(val)) if len(val) < n else val
    if cycle == 'A':
        return start[:4], end[:4]
    elif cycle == 'M':
        # YYYYMM 형식으로 보정
        s = pad(start, 6) if len(start) <= 6 else start[:6]
        e = pad(end, 6) if len(end) <= 6 else end[:6]
        return s, e
    elif cycle == 'Q':
        # YYYYQn 형식
        def to_q(val):
            if 'Q' in val: return val
            if len(val) == 6 and val[4] in '1234':
                return val[:4] + 'Q' + val[5]
            if len(val) == 5 and val[4] in '1234':
                return val[:4] + 'Q' + val[4]
            return val[:4] + 'Q1'
        return to_q(start), to_q(end)
    elif cycle == 'D':
        s = pad(start, 8) if len(start) <= 8 else start[:8]
        e = pad(end, 8) if len(end) <= 8 else end[:8]
        return s, e
    else:
        return start, end

def _load_all_stat_table_rows():
    """모든 StatisticTableList 캐시 파일을 병합하여 row 리스트 반환"""
    import json
    import os
    cache_dir = os.path.join(os.path.dirname(__file__), "../utils/cache")
    files = glob.glob(os.path.join(cache_dir, "StatisticTableList_end-*_start-*.json"))
    all_rows = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            rows = data.get("StatisticTableList", {}).get("row", [])
            if isinstance(rows, dict):
                rows = [rows]
            all_rows.extend(rows)
        except Exception:
            continue
    return all_rows

def ensure_latest_keystatlist_cache():
    cache_path = os.path.join(os.path.dirname(__file__), "../utils/cache/ecos/KeyStatisticList.json")
    # 24시간 이내면 그대로 사용
    if os.path.exists(cache_path):
        mtime = os.path.getmtime(cache_path)
        if time.time() - mtime < 86400:
            return
    # 아니면 최신화
    get_key_statistic_list({"start": 1, "end": 100})

@mcp.tool(
    name="search_realestate_indicators",
    description="""
키워드로 한국은행 ECOS의 100대 주요 통계지표(KeyStatisticList)에서 부동산/금리/가계/투자/거시/심리지표를 검색하고, 관련 지표의 최신값만 요약합니다.

- 이 도구는 무조건 100대 주요지표(KeyStatisticList) 기준으로만 응답합니다.
- keyword: 지표명(예: '기준금리', '주택매매가격지수', '가계신용', '건설투자증감률', '소비자심리지수' 등)
- 결과는 최신값, 단위, 기준일 등만 요약하여 반환합니다.
- data_preview 등 시계열/항목 정보는 제공하지 않습니다.
- 예시: search_realestate_indicators({"keyword": "기준금리"})
""",
    tags={"ECOS", "100대지표", "부동산", "통계", "자동수집", "추천지표"}
)
def search_realestate_indicators(
    params: Annotated[dict, Field(description="검색 파라미터 (keyword)")]
) -> TextContent:
    """
    Always respond based on the 100 KeyStatisticList indicators, returning only filtered/summarized results from that list.
    """
    keyword = params.get("keyword")
    if not keyword:
        return TextContent(type="text", text=json.dumps({"error": "keyword 파라미터는 필수입니다."}, ensure_ascii=False))
    keystat_name_to_row = load_keystat_name_to_row()
    # 유사도/포함 검색 (한글 정규화 포함)
    def norm(s):
        import unicodedata
        return unicodedata.normalize("NFKC", str(s or "")).replace(" ", "")
    norm_kw = norm(keyword)
    matches = []
    for name, row in keystat_name_to_row.items():
        if norm_kw in norm(name) or norm_kw in norm(row.get("KEYSTAT_NAME", "")):
            matches.append(row)
    # 유사도 높은 순 정렬 (간단히 길이 차이 기준)
    matches = sorted(matches, key=lambda r: abs(len(norm(r.get("KEYSTAT_NAME", ""))) - len(norm_kw)))
    # 결과 요약
    result = [
        {
            "stat_name": r.get("KEYSTAT_NAME"),
            "class_name": r.get("CLASS_NAME"),
            "current_value": r.get("DATA_VALUE"),
            "cycle": r.get("CYCLE"),
            "unit": r.get("UNIT_NAME")
        }
        for r in matches
    ]
    if not result:
        return TextContent(type="text", text=json.dumps({"error": "No matching indicator found in the 100 KeyStatisticList.", "keyword": keyword}, ensure_ascii=False, indent=2))
    return TextContent(type="text", text=json.dumps({"keyword": keyword, "results": result}, ensure_ascii=False, indent=2))

# === [핵심 부동산/금리/가계/투자/거시/심리지표명 → ECOS KeyStatisticList 매핑] ===
# 실제 stat_code는 ECOS StatisticTableList/KeyStatisticList에서 매핑 필요. 아래는 예시(실제 코드에서는 자동 매핑/검색도 지원)
REALESTATE_KEY_INDICATORS = {
    "주택매매가격지수": "주택매매가격지수",
    "주택전세가격지수": "주택전세가격지수",
    "지가변동률": "지가변동률(전기대비)",
    "한국은행 기준금리": "한국은행 기준금리",
    "예금은행 대출금리": "예금은행 대출금리",
    "콜금리": "콜금리(익일물)",
    "KORIBOR": "KORIBOR(3개월)",
    "가계신용": "가계신용",
    "가계대출연체율": "가계대출연체율",
    "건설투자증감률": "건설투자증감률(실질, 계절조정 전기대비)",
    "건축허가면적": "건축허가면적",
    "건설기성액": "건설기성액",
    "건축착공면적": "건축착공면적",
    "경제성장률": "경제성장률(실질, 계절조정 전기대비)",
    "M2통화량": "M2(광의통화, 평잔)",
    "소비자심리지수": "소비자심리지수",
    "가구당소득": "가구당월평균소득"
}

def load_keystat_name_to_row():
    """Load the latest KeyStatisticList.json and return a dict mapping KEYSTAT_NAME to row, handling field typos."""
    cache_path = os.path.join(os.path.dirname(__file__), "../utils/cache/ecos/KeyStatisticList.json")
    if not os.path.exists(cache_path):
        return {}
    with open(cache_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("KeyStatisticList", {}).get("row", [])
    # Fix for possible typo in DATA_VALUE field
    for row in rows:
        if "DATA_VALUE" not in row:
            # Use a copy of the keys to avoid changing dict size during iteration
            for k in list(row.keys()):
                if "DATA_VAL" in k:
                    row["DATA_VALUE"] = row[k]
    return {row["KEYSTAT_NAME"].replace("(전기대비)", ""): row for row in rows if "KEYSTAT_NAME" in row}