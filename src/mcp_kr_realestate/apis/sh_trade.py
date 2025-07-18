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

def get_sh_trade_data(lawd_cd: str, deal_ymd: str) -> str:
    """
    단독/다가구 매매 실거래가 API 호출 및 전체 데이터 JSON+통계 반환 (curl subprocess + requests fallback, 반복 수집)
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

    base_url = "https://apis.data.go.kr/1613000/RTMSDataSvcSHTrade/getRTMSDataSvcSHTrade"
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
    df['areaNum'] = get_col(df, '연면적', 'YUA').map(to_num) # 연면적으로 변경
    df['buildYearNum'] = get_col(df, '건축년도', 'buildYear').map(to_num)
    df['dealDayNum'] = get_col(df, '일', 'dealDay').map(to_num)
    
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
    file_path = data_dir / f"SH_TRADE_{lawd_cd}_{deal_ymd}.xml"
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
    return json.dumps(result, ensure_ascii=False) 