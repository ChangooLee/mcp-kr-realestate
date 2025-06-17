"""
환경변수 및 설정 관리
""" 

import os
import logging
from typing import Literal, cast
from dataclasses import dataclass
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class RealEstateConfig:
    """부동산 실거래가 API configuration."""
    api_key: str
    base_url: str = "http://apis.data.go.kr/1613000/RTMSDataSvcNrgTrade/"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file: str = "realestate.log"

    @classmethod
    def from_env(cls) -> "RealEstateConfig":
        api_key = os.getenv("PUBLIC_DATA_API_KEY_ENCODED")
        if not api_key:
            raise ValueError("실거래가 API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")
        return cls(
            api_key=api_key,
            base_url=os.getenv("REALESTATE_BASE_URL", "http://apis.data.go.kr/1613000/RTMSDataSvcNrgTrade/"),
            log_format=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            log_file=os.getenv("LOG_FILE", "realestate.log")
        )

@dataclass
class MCPConfig:
    host: str = "0.0.0.0"
    port: int = 8001
    log_level: str = "INFO"
    server_name: str = "kr-realestate-mcp"
    transport: Literal["stdio", "sse"] = "stdio"

    @classmethod
    def from_env(cls) -> "MCPConfig":
        return cls(
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8001")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            server_name=os.getenv("MCP_SERVER_NAME", "kr-realestate-mcp"),
            transport=cast(Literal["stdio", "sse"], os.getenv("TRANSPORT", "stdio"))
        )

# 설정 인스턴스 생성
def _try_make_config():
    try:
        return RealEstateConfig.from_env()
    except Exception:
        return None

realestate_config = _try_make_config()
mcp_config = MCPConfig.from_env() 