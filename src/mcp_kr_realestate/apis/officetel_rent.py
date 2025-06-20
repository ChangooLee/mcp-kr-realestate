import os
import requests
from pathlib import Path
from dotenv import load_dotenv
import subprocess
import shutil
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import json
from mcp_kr_realestate.apis.molit_api import MolitApiClient

load_dotenv()

def get_officetel_rent_data(lawd_cd: str, deal_ymd: str) -> str:
    """
    오피스텔 전월세 실거래 자료를 조회합니다.
    """
    client = MolitApiClient()
    endpoint = "/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"
    
    # Check for cached data
    cache_dir = os.path.join(os.path.dirname(__file__), '..', 'utils', 'data')
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"OFFICETEL_RENT_{lawd_cd}_{deal_ymd}.json")
    
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            return f.read()

    # Fetch data from API
    all_items = []
    page_no = 1
    total_count = 0
    
    while True:
        xml_data = client.fetch_data(endpoint, lawd_cd, deal_ymd, pageNo=page_no, numOfRows=1000)
        root = ET.fromstring(xml_data)
        
        if page_no == 1:
            total_count_element = root.find('.//totalCount')
            if total_count_element is not None:
                tc_text = total_count_element.text
                if tc_text and tc_text.isdigit():
                    total_count = int(tc_text)
        
        items = root.findall('.//item')
        if not items:
            break
            
        all_items.extend(items)
        
        if total_count == 0 and page_no == 1:
            break
        
        if len(all_items) >= total_count:
            break
        page_no += 1

    if not all_items:
        return json.dumps({"byDong": [], "meta": {"lawd_cd": lawd_cd, "deal_ymd": deal_ymd, "totalCount": 0}}, ensure_ascii=False)

    records = []
    for item in all_items:
        row = {child.tag: child.text for child in item}
        records.append(row)
    
    df = pd.DataFrame(records)

    def to_num(s):
        try:
            return float(str(s).replace(',', '').strip() or 0)
        except (ValueError, TypeError):
            return 0.0

    def to_eok(val):
        try:
            return round(float(val) / 10000, 2) if pd.notna(val) else None
        except (ValueError, TypeError):
            return None

    def get_col_name(df, *names):
        for name in names:
            if name in df.columns:
                return name
        return None

    num_cols_map = {
        'depositNum': ['보증금액', '보증금'],
        'rentFeeNum': ['월세금액', '월세'],
        'areaNum': ['전용면적', 'area', 'excluUseAr'],
        'buildYearNum': ['건축년도', 'buildYear'],
        'floorNum': ['층', 'floor'],
        'dealDayNum': ['일', 'dealDay']
    }
    for new_col, old_cols in num_cols_map.items():
        col_name = get_col_name(df, *old_cols)
        if col_name:
            df[new_col] = df[col_name].map(to_num)
        else:
            df[new_col] = 0.0

    dong_col_name = get_col_name(df, '법정동읍면동명', '법정동', 'umdNm', 'dong')
    if not dong_col_name:
        df['temp_dong'] = '전체'
        dong_col_name = 'temp_dong'

    byDong = []
    for dong, group in df.groupby(dong_col_name):
        jeonse_df = group[group['rentFeeNum'] == 0].copy()
        wolse_df = group[group['rentFeeNum'] > 0].copy()

        jeonse_stats = {}
        if not jeonse_df.empty:
            avg_deposit = float(jeonse_df['depositNum'].mean())
            max_deposit = float(jeonse_df['depositNum'].max())
            min_deposit = float(jeonse_df['depositNum'].min())
            jeonse_stats = {
                'count': len(jeonse_df),
                'avgDeposit': avg_deposit, 'avgDepositEok': to_eok(avg_deposit),
                'maxDeposit': max_deposit, 'maxDepositEok': to_eok(max_deposit),
                'minDeposit': min_deposit, 'minDepositEok': to_eok(min_deposit),
                'deals': jeonse_df.to_dict(orient='records')
            }

        wolse_stats = {}
        if not wolse_df.empty:
            avg_deposit_w = float(wolse_df['depositNum'].mean())
            max_deposit_w = float(wolse_df['depositNum'].max())
            min_deposit_w = float(wolse_df['depositNum'].min())
            avg_rent = float(wolse_df['rentFeeNum'].mean())
            max_rent = float(wolse_df['rentFeeNum'].max())
            min_rent = float(wolse_df['rentFeeNum'].min())
            wolse_stats = {
                'count': len(wolse_df),
                'avgDeposit': avg_deposit_w, 'avgDepositEok': to_eok(avg_deposit_w),
                'maxDeposit': max_deposit_w, 'maxDepositEok': to_eok(max_deposit_w),
                'minDeposit': min_deposit_w, 'minDepositEok': to_eok(min_deposit_w),
                'avgRent': avg_rent,
                'maxRent': max_rent,
                'minRent': min_rent,
                'deals': wolse_df.to_dict(orient='records')
            }
        
        if jeonse_stats or wolse_stats:
            byDong.append({
                'dong': dong.strip(),
                'jeonse': jeonse_stats,
                'wolse': wolse_stats
            })
            
    meta = {"lawd_cd": lawd_cd, "deal_ymd": deal_ymd, "totalCount": total_count}
    result = {"byDong": byDong, "meta": meta}
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
        
    return json.dumps(result, ensure_ascii=False) 