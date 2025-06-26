"""
한국은행 ECOS API 클라이언트
""" 

import os
import requests
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import pandas as pd

ECOS_API_KEY = os.getenv("ECOS_API_KEY")
BASE_URL = "https://ecos.bok.or.kr/api"
CACHE_DIR = Path(__file__).parent.parent / "utils" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _get_cache_path(api_name: str, params: Dict[str, Any]) -> Path:
    """Generate a cache file path based on API name and params."""
    key_parts = [api_name]
    for k, v in sorted(params.items()):
        if v is not None:
            key_parts.append(f"{k}-{v}")
    fname = "_".join(key_parts) + ".json"
    return CACHE_DIR / fname


def _request_ecos_api(service: str, params: Dict[str, Any], endpoint: str) -> dict:
    """Make a request to the ECOS API and return JSON data."""
    api_key = ECOS_API_KEY
    if not api_key:
        raise RuntimeError("ECOS_API_KEY is not set in environment variables.")
    url_parts = [BASE_URL, endpoint, api_key, "json", "kr"]
    # Required pagination params
    start = str(params.get("start", 1))
    end = str(params.get("end", 100))
    url_parts += [start, end]
    # Optional code params
    if "stat_code" in params and params["stat_code"]:
        url_parts.append(str(params["stat_code"]))
    if "word" in params and params["word"]:
        url_parts.append(str(params["word"]))
    # For StatisticSearch, use query string
    url = "/".join(url_parts)
    if endpoint == "StatisticSearch":
        # For StatisticSearch, use query string for extra params
        url = f"{BASE_URL}/{endpoint}/{api_key}/json/kr/{start}/{end}/{params['stat_code']}/{params['cycle']}/{params['start_time']}/{params['end_time']}"
        for i in range(1, 5):
            code = params.get(f"item_code{i}")
            if code:
                url += f"/{code}"
    resp = requests.get(url)
    if resp.status_code != 200:
        raise RuntimeError(f"ECOS API request failed: {resp.status_code} {resp.text}")
    data = resp.json()
    # ECOS API error handling
    if isinstance(data, dict) and "RESULT" in data:
        result = data["RESULT"]
        if result.get("CODE") not in ("INFO-000", "INFO-200"):
            raise RuntimeError(f"ECOS API error: {result.get('CODE')} {result.get('MESSAGE')}")
    return data


def get_statistic_table_list(params: Dict[str, Any]) -> Path:
    """서비스 통계 목록 조회 및 캐싱. Returns cache file path."""
    cache_path = _get_cache_path("StatisticTableList", params)
    if cache_path.exists():
        return cache_path
    data = _request_ecos_api("StatisticTableList", params, "StatisticTableList")
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return cache_path


def get_statistic_word(params: Dict[str, Any]) -> Path:
    """통계용어사전 조회 및 캐싱. Returns cache file path."""
    cache_path = _get_cache_path("StatisticWord", params)
    if cache_path.exists():
        return cache_path
    data = _request_ecos_api("StatisticWord", params, "StatisticWord")
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return cache_path


def get_statistic_item_list(params: Dict[str, Any]) -> Path:
    """통계 세부항목 목록 조회 및 캐싱. Returns cache file path."""
    cache_path = _get_cache_path("StatisticItemList", params)
    if cache_path.exists():
        return cache_path
    data = _request_ecos_api("StatisticItemList", params, "StatisticItemList")
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return cache_path


def get_statistic_search(params: Dict[str, Any]) -> Path:
    """통계 조회조건 설정(데이터 조회) 및 캐싱. Returns cache file path."""
    cache_path = _get_cache_path("StatisticSearch", params)
    if cache_path.exists():
        return cache_path
    data = _request_ecos_api("StatisticSearch", params, "StatisticSearch")
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return cache_path


def get_key_statistic_list(params: Dict[str, Any]) -> Path:
    """100대 통계지표 조회 및 캐싱. Returns cache file path."""
    cache_path = _get_cache_path("KeyStatisticList", params)
    if cache_path.exists():
        return cache_path
    data = _request_ecos_api("KeyStatisticList", params, "KeyStatisticList")
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return cache_path

# (추후 analysis_tools.py에서 도구로 등록) 