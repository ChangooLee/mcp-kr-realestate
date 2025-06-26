"""
한국부동산원 R-ONE API 클라이언트
""" 

import os
import requests
import json
import pandas as pd
from pathlib import Path

REB_API_BASE = "https://www.reb.or.kr/r-one/openapi"
REB_API_KEY = os.getenv("REB_API_KEY", "sample key")

def _reb_api_request(endpoint, params, cache_prefix):
    params = params.copy()
    params["KEY"] = REB_API_KEY
    params["Type"] = "json"
    params.setdefault("pIndex", 1)
    params.setdefault("pSize", 100)
    cache_dir = Path(__file__).parent.parent / "utils" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = f"{cache_prefix}_" + str(abs(hash(json.dumps(params, sort_keys=True, ensure_ascii=False)))) + ".json"
    cache_path = cache_dir / cache_key
    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    url = f"{REB_API_BASE}/{endpoint}"
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return data

def get_reb_stat_list(params):
    return _reb_api_request("SttsApiTbl.do", params, "stat_list")

def get_reb_stat_items(params):
    return _reb_api_request("SttsApiTblItm.do", params, "stat_items")

def get_reb_stat_data(params):
    return _reb_api_request("SttsApiTblData.do", params, "stat_data")

def _reb_api_collect_all(endpoint, params, cache_prefix, page_size=100):
    params = params.copy()
    params["KEY"] = REB_API_KEY
    params["Type"] = "json"
    params["pSize"] = page_size
    all_results = []
    page = 1
    while True:
        params["pIndex"] = page
        data = _reb_api_request(endpoint, params, f"{cache_prefix}_p{page}")
        # --- 응답 구조별 파싱 ---
        items = []
        if "SttsApiTbl" in data:
            stts = data["SttsApiTbl"]
            for entry in stts:
                if "row" in entry:
                    items = entry["row"]
                    break
        elif "result" in data:
            items = data["result"].get("list", []) or data["result"].get("items", []) or []
        elif "row" in data:
            items = data["row"]
        # 기타 구조도 대응
        if not items:
            break
        all_results.extend(items)
        if len(items) < page_size:
            break
        page += 1
    # 캐시 전체 저장
    cache_dir = Path(__file__).parent.parent / "utils" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{cache_prefix}_all.json"
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False)
    return all_results

def get_reb_stat_list_all(params, page_size=100):
    return _reb_api_collect_all("/SttsApiTbl.do", params, "stat_list", page_size=page_size)

def get_reb_stat_items_all(params, page_size=100):
    return _reb_api_collect_all("/SttsApiTblItm.do", params, "stat_items", page_size=page_size)

def get_reb_stat_data_all(params, page_size=100):
    all_items = _reb_api_collect_all("/SttsApiTblData.do", params, "stat_data", page_size=page_size)
    # 최신 데이터 우선 정렬
    # all_items가 SttsApiTblData의 row 리스트인지 확인, 아니라면 파싱
    if all_items and isinstance(all_items, dict) and "SttsApiTblData" in all_items:
        rows = []
        for entry in all_items["SttsApiTblData"]:
            if "row" in entry:
                rows.extend(entry["row"])
        all_items = rows
    elif all_items and isinstance(all_items, list) and all(isinstance(x, dict) and "row" in x for x in all_items):
        # 혹시 여러 page의 row가 합쳐진 경우
        rows = []
        for entry in all_items:
            if "row" in entry:
                rows.extend(entry["row"])
        all_items = rows
    # row만 남기고 저장
    df = pd.DataFrame(all_items)
    if "WRTTIME_IDTFR_ID" in df.columns:
        df = df.sort_values(by="WRTTIME_IDTFR_ID", ascending=False)
    return df.to_dict(orient="records")

def cache_stat_list_full(params, page_size=100):
    all_items = get_reb_stat_list_all(params, page_size=page_size)
    cache_dir = Path(__file__).parent.parent / "utils" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "stat_list_full.json"
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False)
    return cache_path

def cache_stat_list(params, page_size=100):
    all_items = get_reb_stat_list_all(params, page_size=page_size)
    cache_dir = Path(__file__).parent.parent / "utils" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = str(abs(hash(json.dumps(params, sort_keys=True, ensure_ascii=False))))
    cache_path = cache_dir / f"stat_list_{key}.json"
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False)
    return cache_path

def _get_data_cache_path(statbl_id):
    return str((Path(__file__).parent.parent / "utils" / "cache" / f"stat_data_{statbl_id}.json")) 