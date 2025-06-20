import os
import requests
from pathlib import Path
from dotenv import load_dotenv
import json
import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET

load_dotenv()

"""
국토교통부 실거래가 API 클라이언트
"""

def get_nrg_trade_data(lawd_cd: str, deal_ymd: str) -> str:
    """
    상업업무용 부동산 매매 실거래가 API 호출 및 XML 저장
    Args:
        lawd_cd (str): 법정동코드 5자리
        deal_ymd (str): 거래년월 (YYYYMM)
    Returns:
        str: 저장된 XML 파일 경로
    """
    api_key = os.environ.get("PUBLIC_DATA_API_KEY_ENCODED")
    if not api_key:
        raise ValueError("환경변수 PUBLIC_DATA_API_KEY_ENCODED가 설정되어 있지 않습니다.")

    base_url = "http://apis.data.go.kr/1613000/RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade"
    headers = {"serviceKey": api_key}
    params = {
        'LAWD_CD': lawd_cd,
        'DEAL_YMD': deal_ymd,
        'stdt': deal_ymd[:4],  # 조회시작년도(YYYY)
    }
    response = requests.get(base_url, params=params, headers=headers, verify=False)
    response.raise_for_status()

    # 저장 경로
    data_dir = Path(__file__).parent.parent / "utils" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    file_path = data_dir / f"NRG_{lawd_cd}_{deal_ymd}.xml"
    with open(file_path, "wb") as f:
        f.write(response.content)

    # 반복적으로 전체 데이터 수집 (아파트와 동일)
    all_items = []
    total_count = None
    num_of_rows = 100
    page_no = 1
    while True:
        params = {
            'LAWD_CD': lawd_cd,
            'DEAL_YMD': deal_ymd,
            'serviceKey': api_key,
            'numOfRows': num_of_rows,
            'pageNo': page_no
        }
        data = None
        try:
            resp = requests.get(base_url, params=params, headers={"User-Agent": "Mozilla/5.0"}, verify=False, timeout=30)
            resp.raise_for_status()
            data = resp.text
        except Exception as e:
            raise RuntimeError(f"실거래가 API 요청 실패: {e}")
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
        for n in names:
            if n in df.columns:
                return n
        return names[0]
    df['dealAmountNum'] = get_col(df, '거래금액', 'dealAmount').map(lambda x: to_num(x))
    df['areaNum'] = get_col(df, '전용면적', 'area', 'excluUseAr').map(lambda x: to_num(x))
    df['buildYearNum'] = get_col(df, '건축년도', 'buildYear').map(lambda x: to_num(x))
    df['floorNum'] = get_col(df, '층', 'floor').map(lambda x: to_num(x))
    df['dealDayNum'] = get_col(df, '일', 'dealDay').map(lambda x: to_num(x))
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
            'count': len(group),
            'avgAmount': avg,
            'avgAmountEok': to_eok(avg),
            'maxAmount': mx,
            'maxAmountEok': to_eok(mx),
            'minAmount': mn,
            'minAmountEok': to_eok(mn),
            'deals': deals
        })
    meta = {"lawd_cd": lawd_cd, "deal_ymd": deal_ymd, "totalCount": len(df)}
    return json.dumps({"byDong": byDong, "meta": meta}, ensure_ascii=False)

    # (옵션) 원본 XML 저장 (반복 수집 후)
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