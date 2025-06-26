"""
데이터 전처리
""" 
import os
import sys
import tempfile
from pathlib import Path

def get_cache_dir():
    """
    Returns a cross-platform, user-writable cache directory.
    Priority:
    1. MCP_REAL_ESTATE_CACHE_DIR environment variable
    2. OS user cache dir (~/AppData/Local on Windows, ~/.cache on Unix)
    3. /tmp (as last resort)
    """
    # 1. 환경변수 우선
    cache_dir = os.environ.get("MCP_REAL_ESTATE_CACHE_DIR")
    if cache_dir:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        return cache_dir
    # 2. OS별 표준 사용자 캐시 디렉토리
    if sys.platform == "win32":
        local_appdata = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
        cache_dir = os.path.join(local_appdata, "mcp-kr-realestate-cache")
    else:
        cache_dir = os.path.expanduser("~/.cache/mcp-kr-realestate")
    try:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        return cache_dir
    except Exception:
        pass
    # 3. /tmp (공유 불가, 임시)
    tmp_cache = os.path.join(tempfile.gettempdir(), "mcp-kr-realestate-cache")
    Path(tmp_cache).mkdir(parents=True, exist_ok=True)
    return tmp_cache 