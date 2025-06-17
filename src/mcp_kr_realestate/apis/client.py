import os
import requests
from dotenv import load_dotenv
from urllib.parse import urljoin
import json
import logging
from typing import Dict, Any, Optional
import zipfile
import io
from mcp_kr_realestate.config import RealEstateConfig, realestate_config

load_dotenv()

logger = logging.getLogger(__name__)

class RealEstateClient:
    """부동산 실거래가 API 클라이언트"""
    def __init__(self, config: Optional[RealEstateConfig] = None):
        self.config = config or realestate_config
        self.api_key = self.config.api_key
        self.base_url = self.config.base_url
        if not self.api_key:
            raise ValueError("실거래가 API 키가 설정되지 않았습니다.")

    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None, method: str = "GET") -> Dict[str, Any]:
        if params is None:
            params = {}
        params["serviceKey"] = self.api_key
        url = urljoin(self.base_url, endpoint)
        logger.debug(f"\n=== API 요청 정보 ===")
        logger.debug(f"URL: {url}")
        logger.debug(f"Method: {method}")
        logger.debug(f"Parameters: {params}")
        logger.debug("====================")
        try:
            if method.upper() == "GET":
                response = requests.get(url, params=params)
            elif method.upper() == "POST":
                response = requests.post(url, data=params)
            else:
                raise ValueError(f"지원하지 않는 HTTP 메서드: {method}")
            logger.debug(f"\n=== API 응답 정보 ===")
            logger.debug(f"상태 코드: {response.status_code}")
            logger.debug(f"Content-Type: {response.headers.get('Content-Type', '없음')}")
            if "application/json" in response.headers.get("Content-Type", ""):
                logger.debug(f"응답 내용: {response.text}")
            logger.debug("====================")
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                data: Dict[str, Any] = response.json()
                return data
            elif "application/zip" in content_type or "application/x-zip-compressed" in content_type:
                return {"status": "000", "message": "정상", "content": response.content}
            elif "text/xml" in content_type or "application/xml" in content_type:
                return {"status": "000", "message": "정상", "content": response.text}
            else:
                try:
                    zip_file = zipfile.ZipFile(io.BytesIO(response.content))
                    return {"status": "000", "message": "정상", "content": response.content}
                except:
                    return {"status": "000", "message": "정상", "content": response.text}
        except requests.RequestException as e:
            logger.error(f"API 요청 실패: {str(e)}")
            return {"error": str(e), "status_code": getattr(e.response, 'status_code', None)}

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._make_request(endpoint, params, "GET")

    def post(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._make_request(endpoint, params, "POST")

    def download(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if params is None:
            params = {}
        params["serviceKey"] = self.api_key
        url = urljoin(self.base_url, endpoint)
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            logger.debug(f"\n=== API 응답 정보 ===")
            logger.debug(f"상태 코드: {response.status_code}")
            logger.debug(f"Content-Type: {response.headers.get('Content-Type', '없음')}")
            logger.debug("====================")
            return {"status": "000", "message": "정상", "content": response.content}
        except requests.RequestException as e:
            logger.error(f"파일 다운로드 실패: {str(e)}")
            return {"error": str(e), "status_code": getattr(e.response, 'status_code', None)}

"""
공통 HTTP 클라이언트
""" 