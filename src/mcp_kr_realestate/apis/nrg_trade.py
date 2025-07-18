from typing import Dict, Any, Optional
from mcp_kr_realestate.apis.client import RealEstateClient
from pathlib import Path
import os
import xml.etree.ElementTree as ET
import requests
import pandas as pd
import numpy as np
import json
from dotenv import load_dotenv
import subprocess
import shutil

load_dotenv()

class NRGTradeAPI:
    """상업업무용 부동산 실거래가 API"""
    def __init__(self, client: RealEstateClient):
        self.client = client
        self.api_key = self.client.api_key or os.environ.get("PUBLIC_DATA_API_KEY_ENCODED")

    def get_trade_data(self, lawd_cd: str, deal_ymd: str) -> str:
        """
        상업업무용 부동산 매매 실거래가 전체 데이터 조회 및 처리 (apt_trade.py 기준)
        Args:
            lawd_cd (str): 법정동코드 (5자리 이상, 앞 5자리만 사용)
            deal_ymd (str): 거래년월 (YYYYMM)
        Returns:
            str: 전체 거래 데이터와 통계가 포함된 JSON 문자열
        """
        if not self.api_key:
            raise ValueError("환경변수 PUBLIC_DATA_API_KEY_ENCODED가 설정되어 있지 않습니다.")

        # 법정동코드 앞 5자리만 사용
        lawd_cd = str(lawd_cd)[:5]

        base_url = "https://apis.data.go.kr/1613000/RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade"
        
        all_items = []
        total_count = None
        num_of_rows = 100
        page_no = 1
        
        while True:
            params = {
                'LAWD_CD': lawd_cd,
                'DEAL_YMD': deal_ymd,
                'serviceKey': self.api_key,
                'numOfRows': str(num_of_rows),
                'pageNo': str(page_no)
            }
            data = None

            # apt_trade.py와 동일하게 curl 우선 사용
            curl_url = f"{base_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            curl_path = shutil.which("curl")

            if curl_path:
                try:
                    result = subprocess.run(
                        [curl_path, "-s", "-g", "-H", f"User-Agent: {user_agent}", curl_url],
                        capture_output=True, text=True, check=True, encoding='utf-8'
                    )
                    data = result.stdout
                except Exception:
                    pass  # requests로 fallback

            if data is None:
                try:
                    resp = requests.get(base_url, params=params, headers={"User-Agent": user_agent}, verify=False, timeout=30)
                    resp.raise_for_status()
                    data = resp.text
                except Exception as e:
                    raise RuntimeError(f"실거래가 API 요청 실패 (curl, requests 모두 실패): {e}")
            
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
            
            if not items or (total_count is not None and len(all_items) >= total_count):
                break
            page_no += 1

        # XML -> JSON 변환 및 데이터 처리 (apt_trade.py 방식 적용)
        records = []
        for item in all_items:
            records.append({child.tag: child.text for child in item})
        
        if not records:
            return json.dumps({"byDong": [], "meta": {"lawd_cd": lawd_cd, "deal_ymd": deal_ymd, "totalCount": 0}}, ensure_ascii=False)
        
        df = pd.DataFrame(records)
        
        def to_num(s):
            try: return float(str(s).replace(',', ''))
            except (ValueError, TypeError): return np.nan

        def to_eok(val):
            try: return round(float(val) / 10000, 2) if pd.notna(val) else None
            except (ValueError, TypeError): return None

        def get_col(df, *names):
            for n in names:
                if n in df.columns: return df[n]
            return pd.Series(np.nan, index=df.index)

        df['dealAmountNum'] = get_col(df, '거래금액', 'dealAmount').apply(to_num)
        df['areaNum'] = get_col(df, '전용면적', 'area', 'excluUseAr').apply(to_num)
        df['buildYearNum'] = get_col(df, '건축년도', 'buildYear').apply(to_num)
        df['floorNum'] = get_col(df, '층', 'floor').apply(to_num)
        df['dealDayNum'] = get_col(df, '일', 'dealDay').apply(to_num)

        dong_col = get_col(df, '법정동', 'umdNm', 'dong')
        byDong = []
        if dong_col.notna().any():
            for dong, group in df.groupby(dong_col):
                group = group.dropna(subset=['dealAmountNum'])
                if group.empty: continue
                
                avg = float(group['dealAmountNum'].mean())
                mx = float(group['dealAmountNum'].max())
                mn = float(group['dealAmountNum'].min())
                deals = group.to_dict(orient='records')
                
                byDong.append({
                    'dong': dong.strip(),
                    'count': len(group),
                    'avgAmount': avg, 'avgAmountEok': to_eok(avg),
                    'maxAmount': mx, 'maxAmountEok': to_eok(mx),
                    'minAmount': mn, 'minAmountEok': to_eok(mn),
                    'deals': deals
                })

        meta = {"lawd_cd": lawd_cd, "deal_ymd": deal_ymd, "totalCount": len(df)}
        
        # 파일 저장 로직 (apt_trade.py 참고)
        data_dir = Path(__file__).parent.parent / "utils" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        file_path = data_dir / f"NRG_{lawd_cd}_{deal_ymd}.xml"
        
        response_root = ET.Element('response')
        header = ET.SubElement(response_root, 'header')
        ET.SubElement(header, 'resultCode').text = '00'
        ET.SubElement(header, 'resultMsg').text = 'NORMAL SERVICE.'
        body = ET.SubElement(response_root, 'body')
        items_elem = ET.SubElement(body, 'items')
        for item in all_items:
            items_elem.append(item)
        ET.SubElement(body, 'numOfRows').text = str(num_of_rows)
        ET.SubElement(body, 'pageNo').text = str(page_no)
        ET.SubElement(body, 'totalCount').text = str(total_count if total_count is not None else len(all_items))
        
        xml_str = ET.tostring(response_root, encoding='utf-8', method='xml').decode('utf-8')
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(xml_str)
            
        return json.dumps({"byDong": byDong, "meta": meta, "saved_path": str(file_path)}, ensure_ascii=False)

    def get_region_codes(self) -> Dict[str, Any]:
        """
        법정동 코드 전체 조회 (예시)
        Returns:
            Dict[str, Any]: API 응답
        """
        endpoint = "getRTMSDataSvcLawdCode"
        response = self.client.get(endpoint)
        return response 