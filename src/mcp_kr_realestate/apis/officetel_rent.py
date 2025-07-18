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

load_dotenv()

def get_officetel_rent_data(lawd_cd: str, deal_ymd: str) -> str:
    """
    오피스텔 전월세 실거래가 API 호출 및 전체 데이터 JSON+통계 반환 (curl subprocess + requests fallback, 반복 수집)
    Args:
        lawd_cd (str): 법정동코드 (5자리 이상, 앞 5자리만 사용)
        deal_ymd (str): 거래년월 (YYYYMM)
    Returns:
        str: 전체 거래 데이터와 통계가 포함된 JSON 문자열
    """
    api_key = os.environ.get("PUBLIC_DATA_API_KEY_ENCODED")
    if not api_key:
        raise ValueError("환경변수 PUBLIC_DATA_API_KEY_ENCODED가 설정되어 있지 않습니다.")

    # 법정동코드 앞 5자리만 사용
    lawd_cd = str(lawd_cd)[:5]

    base_url = "https://apis.data.go.kr/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"
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
        return json.dumps({"byDong": [], "meta": {"lawd_cd": lawd_cd, "deal_ymd": deal_ymd, "totalCount": 0}}, ensure_ascii=False)
    
    df = pd.DataFrame(records)

    def to_num(s):
        try:
            return float(str(s).replace(',', ''))
        except (ValueError, TypeError):
            return np.nan

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

    # 숫자형 컬럼 생성 (안전하게)
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
            df[new_col] = np.nan
    
    # NaN 값을 0으로 채워서 숫자형으로 통일
    df['depositNum'] = df['depositNum'].fillna(0)
    df['rentFeeNum'] = df['rentFeeNum'].fillna(0)

    dong_col_name = get_col_name(df, '법정동', 'umdNm', 'dong')
    if not dong_col_name:
        df['temp_dong'] = '전체'
        dong_col_name = 'temp_dong'

    byDong = []
    for dong, group in df.groupby(dong_col_name):
        # 전세, 월세 분리
        jeonse_df = group[group['rentFeeNum'] == 0].copy()
        wolse_df = group[group['rentFeeNum'] > 0].copy()

        # 전세 통계
        jeonse_stats = {}
        if not jeonse_df.empty:
            avg_deposit = float(jeonse_df['depositNum'].mean())
            max_deposit = float(jeonse_df['depositNum'].max())
            min_deposit = float(jeonse_df['depositNum'].min())
            jeonse_stats = {
                'count': len(jeonse_df),
                'avgDeposit': avg_deposit,
                'avgDepositEok': to_eok(avg_deposit),
                'maxDeposit': max_deposit,
                'maxDepositEok': to_eok(max_deposit),
                'minDeposit': min_deposit,
                'minDepositEok': to_eok(min_deposit),
                'deals': jeonse_df.to_dict(orient='records')
            }

        # 월세 통계
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
                'avgDeposit': avg_deposit_w,
                'avgDepositEok': to_eok(avg_deposit_w),
                'maxDeposit': max_deposit_w,
                'maxDepositEok': to_eok(max_deposit_w),
                'minDeposit': min_deposit_w,
                'minDepositEok': to_eok(min_deposit_w),
                'avgRent': avg_rent,
                'maxRent': max_rent,
                'minRent': min_rent,
                'deals': wolse_df.to_dict(orient='records')
            }
        
        if jeonse_stats or wolse_stats:
            byDong.append({
                'dong': dong,
                'jeonse': jeonse_stats,
                'wolse': wolse_stats
            })

    meta = {"lawd_cd": lawd_cd, "deal_ymd": deal_ymd, "totalCount": total_count}
    response_json = {"byDong": byDong, "meta": meta}
    
    # (옵션) 원본 XML 저장
    data_dir = Path(__file__).parent.parent / "utils" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    file_path = data_dir / f"OFFICETEL_RENT_{lawd_cd}_{deal_ymd}.xml"
    response_root = ET.Element('response')
    header = ET.SubElement(response_root, 'header')
    ET.SubElement(header, 'resultCode').text = '000'
    ET.SubElement(header, 'resultMsg').text = 'OK'
    body = ET.SubElement(response_root, 'body')
    items_elem = ET.SubElement(body, 'items')
    for item in all_items:
        items_elem.append(item)
    ET.SubElement(body, 'numOfRows').text = str(num_of_rows)
    ET.SubElement(body, 'pageNo').text = '1'
    ET.SubElement(body, 'totalCount').text = str(total_count if total_count is not None else len(all_items))
    xml_str = ET.tostring(response_root, encoding='utf-8', method='xml').decode('utf-8')
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(xml_str)
        
    return json.dumps(response_json, ensure_ascii=False) 