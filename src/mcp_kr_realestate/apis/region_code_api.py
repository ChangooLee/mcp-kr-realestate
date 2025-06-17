import os
import requests
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

"""
법정동 코드 조회 API 클라이언트
"""

def get_region_codes(page: int = 1, per_page: int = 1000, return_type: str = "JSON") -> Dict[str, Any]:
    """
    국토교통부 전국 법정동 코드 목록을 조회합니다.
    Args:
        page (int): 페이지 번호 (기본값 1)
        per_page (int): 페이지당 데이터 수 (기본값 1000)
        return_type (str): 응답 데이터 타입 (JSON 또는 XML)
    Returns:
        dict: API 응답(JSON)
    """
    api_key = os.environ.get("PUBLIC_DATA_API_KEY_ENCODED")
    if not api_key:
        raise ValueError("환경변수 PUBLIC_DATA_API_KEY_ENCODED가 설정되어 있지 않습니다.")

    base_url = "https://api.odcloud.kr/api/15063424/v1/uddi:257e1510-0eeb-44de-8883-8295c94dadf7"
    url = f"{base_url}?serviceKey={api_key}"
    params = {
        "page": page,
        "perPage": per_page,
        "returnType": return_type,
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json() 