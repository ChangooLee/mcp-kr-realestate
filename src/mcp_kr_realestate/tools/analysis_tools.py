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

def analyze_commercial_property_data(df: pd.DataFrame) -> Dict[str, Any]:
    """DataFrame을 받아 상업업무용 부동산 통계를 분석하고 JSON으로 반환합니다."""
    
    if df.empty:
        return {"error": "분석할 데이터가 없습니다."}

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
        return {"error": "정리 후 유효한 거래 데이터가 없습니다."}

    df['평당가_만원'] = (df['거래금액_num'] / df['전용면적_num']) * 3.305785
    
    current_year = datetime.now().year
    df['건물연령'] = current_year - df['건축년도_num']

    # --- 1. 종합 통계 ---
    total_count = len(df)
    total_value = df['거래금액_num'].sum()
    property_type_col = '주용도' if '주용도' in df.columns else '유형'
    type_distribution = df[property_type_col].value_counts().to_dict() if property_type_col in df.columns else {}

    overall_stats = {
        "총 거래 건수": total_count,
        "총 거래 대금 (만원)": total_value,
        "용도별 거래 분포": type_distribution
    }

    # --- 2. 가격 수준 통계 ---
    price_stats = {
        "전체 평균 거래가 (만원)": df['거래금액_num'].mean(),
        "전체 중위 거래가 (만원)": df['거래금액_num'].median(),
        "전체 최고 거래가 (만원)": df['거래금액_num'].max(),
        "전체 최저 거래가 (만원)": df['거래금액_num'].min()
    }
    if property_type_col in df.columns:
        price_by_type = df.groupby(property_type_col)['거래금액_num'].agg(['mean', 'median', 'max', 'min']).to_dict('index')
        price_stats["용도별 가격 통계 (만원)"] = price_by_type

    # --- 3. 단위 면적당 가격 통계 ---
    price_per_area_stats = {
        "전체 평균 평당가 (만원/평)": df['평당가_만원'].mean(),
        "전체 중위 평당가 (만원/평)": df['평당가_만원'].median()
    }
    if property_type_col in df.columns:
        price_per_area_by_type = df.groupby(property_type_col)['평당가_만원'].agg(['mean', 'median']).to_dict('index')
        price_per_area_stats["용도별 평당가 통계 (만원/평)"] = price_per_area_by_type

    # --- 4. 입지별 통계 (동별) ---
    location_col = '법정동' if '법정동' in df.columns else 'dong'
    location_stats = {}
    if location_col in df.columns and df[location_col].notna().any():
        location_grouped = df.groupby(location_col)
        location_summary = location_grouped['거래금액_num'].agg(Count='size', Mean='mean', Max='max', Min='min').to_dict('index')
        location_ppa_summary = location_grouped['평당가_만원'].agg(Mean_PPA='mean', Median_PPA='median').to_dict('index')
        for dong, stats in location_summary.items():
            stats.update(location_ppa_summary.get(dong, {}))
        location_stats = location_summary

    # --- 5. 건물 특성별 통계 ---
    age_bins = [0, 6, 11, 21, np.inf]
    age_labels = ['5년 이내 (신축)', '6-10년', '11-20년', '20년 초과']
    df['건물연령대'] = pd.cut(df['건물연령'], bins=age_bins, labels=age_labels, right=False)
    age_stats = {}
    if not df['건물연령대'].isnull().all():
        age_summary = df.groupby('건물연령대', observed=True)['거래금액_num'].agg(Count='size', Mean_Price='mean').to_dict('index')
        age_ppa_summary = df.groupby('건물연령대', observed=True)['평당가_만원'].agg(Mean_PPA='mean').to_dict()
        for age_group, stats in age_summary.items():
            stats.update(age_ppa_summary.get(age_group, {}))
        age_stats = age_summary

    area_bins = [0, 100, 300, 1000, np.inf]
    area_labels = ['소형 (<100m²)', '중형 (100-300m²)', '대형 (300-1000m²)', '초대형 (>1000m²)']
    df['건물규모'] = pd.cut(df['전용면적_num'], bins=area_bins, labels=area_labels, right=False)
    scale_stats = {}
    if not df['건물규모'].isnull().all():
        scale_summary = df.groupby('건물규모', observed=True)['거래금액_num'].agg(Count='size', Mean_Price='mean').to_dict('index')
        scale_ppa_summary = df.groupby('건물규모', observed=True)['평당가_만원'].agg(Mean_PPA='mean').to_dict()
        for scale_group, stats in scale_summary.items():
            stats.update(scale_ppa_summary.get(scale_group, {}))
        scale_stats = scale_summary

    building_stats = {"건축 연령대별 통계": age_stats, "건물 규모별 통계 (전용면적 기준)": scale_stats}

    return {
        "종합 통계": overall_stats,
        "가격 수준 통계": price_stats,
        "단위 면적당 가격 통계": price_per_area_stats,
        "입지별 통계 (동별)": location_stats,
        "건물 특성별 통계": building_stats,
        "주의사항": "평당가 및 건물 규모는 '전용면적'을 기준으로 계산되었으며, '대지 지분' 또는 '도로 조건' 데이터는 API에서 제공되지 않아 분석에 포함되지 않았습니다."
    }

@mcp.tool(
    name="analyze_commercial_property_trade",
    description="""상업업무용 부동산(상가, 오피스 등) 매매 실거래 데이터 파일을 분석하여 월간 리포트 형식의 핵심 통계 요약을 제공합니다.
이 도구는 `get_commercial_property_trade_data`를 통해 얻은 데이터 파일의 경로를 입력받아 작동합니다.
종합 통계, 가격 수준, 평당가, 입지별, 건물 특성별 등 다각적인 분석 결과를 반환하여 시장 동향을 깊이 있게 파악할 수 있도록 돕습니다.

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