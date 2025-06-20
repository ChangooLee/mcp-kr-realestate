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

class MolitApiClient:
    def __init__(self):
        self.api_key = os.environ.get("PUBLIC_DATA_API_KEY_ENCODED")
        if not self.api_key:
            raise ValueError("환경변수 PUBLIC_DATA_API_KEY_ENCODED가 설정되어 있지 않습니다.")
        self.base_url = "http://apis.data.go.kr/1613000"
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        self.curl_path = shutil.which("curl")

    def fetch_data(self, endpoint: str, lawd_cd: str, deal_ymd: str, pageNo: int = 1, numOfRows: int = 1000) -> str:
        url = f"{self.base_url}{endpoint}"
        params = {
            'LAWD_CD': lawd_cd,
            'DEAL_YMD': deal_ymd,
            'serviceKey': self.api_key,
            'numOfRows': numOfRows,
            'pageNo': pageNo
        }
        
        param_str = "&".join([f"{k}={v}" for k, v in params.items()])
        curl_url = f"{url}?{param_str}"

        if self.curl_path:
            try:
                result = subprocess.run(
                    [self.curl_path, "-s", "-H", f"User-Agent: {self.user_agent}", curl_url],
                    capture_output=True, check=True
                )
                return result.stdout.decode('utf-8')
            except Exception:
                pass  # fallback to requests

        try:
            response = requests.get(url, params=params, headers={"User-Agent": self.user_agent}, verify=False, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            raise RuntimeError(f"Both curl and requests failed to fetch data: {e}")

# 기존 함수들은 삭제 또는 비활성화 (MolitApiClient로 대체)
# def get_nrg_trade_data ... 