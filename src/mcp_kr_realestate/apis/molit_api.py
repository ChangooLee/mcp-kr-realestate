import os
import requests
from pathlib import Path
from dotenv import load_dotenv

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
    return str(file_path) 