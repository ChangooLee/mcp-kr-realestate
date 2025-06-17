from typing import Dict, Any, Optional
from mcp_kr_realestate.apis.client import RealEstateClient
from pathlib import Path
import os
import xml.etree.ElementTree as ET

class NRGTradeAPI:
    """상업업무용 부동산 실거래가 API"""
    def __init__(self, client: RealEstateClient):
        self.client = client

    def get_trade_data(self, lawd_cd: str, deal_ymd: str) -> Dict[str, Any]:
        """
        실거래가 데이터 조회 및 XML 저장
        Args:
            lawd_cd (str): 법정동코드 5자리
            deal_ymd (str): 거래년월 (YYYYMM)
        Returns:
            Dict[str, Any]: API 응답 및 저장 경로
        """
        endpoint = "getRTMSDataSvcNrgTrade"
        params = {"LAWD_CD": lawd_cd, "DEAL_YMD": deal_ymd}
        response = self.client.get(endpoint, params)
        # 저장 경로
        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / "utils" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        xml_path = data_dir / f"NRG_{lawd_cd}_{deal_ymd}.xml"
        if response.get("status") == "000" and response.get("content"):
            with open(xml_path, "w", encoding="utf-8") as f:
                f.write(response["content"])
            response["saved_path"] = str(xml_path)
        return response

    def get_region_codes(self) -> Dict[str, Any]:
        """
        법정동 코드 전체 조회 (예시)
        Returns:
            Dict[str, Any]: API 응답
        """
        endpoint = "getRTMSDataSvcLawdCode"
        response = self.client.get(endpoint)
        return response 