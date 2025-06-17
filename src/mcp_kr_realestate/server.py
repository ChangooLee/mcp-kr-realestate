"""
FastMCP 서버 메인 엔트리포인트
""" 

import logging
import sys
import asyncio
from starlette.requests import Request
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated, Any, Literal, Optional
from fastmcp import FastMCP
from mcp_kr_realestate.config import MCPConfig, RealEstateConfig, mcp_config, realestate_config
from mcp_kr_realestate.apis.client import RealEstateClient
from mcp_kr_realestate.apis.nrg_trade import NRGTradeAPI
from mcp_kr_realestate.registry.initialize_registry import initialize_registry
import importlib

# 로깅 설정
level_name = mcp_config.log_level.upper()
level = getattr(logging, level_name, logging.INFO)
logger = logging.getLogger("mcp-kr-realestate")
logging.basicConfig(
    level=level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)

@dataclass
class RealEstateContext:
    client: Optional[RealEstateClient] = None
    nrg_trade: Any = None

    def __post_init__(self):
        if self.client is None:
            self.client = RealEstateClient(config=realestate_config)
        if self.nrg_trade is None:
            self.nrg_trade = NRGTradeAPI(self.client)

    async def __aenter__(self):
        logger.info("🔁 RealEstateContext entered (Claude requested tool execution)")
        return self

    async def __aexit__(self, *args):
        logger.info("🔁 RealEstateContext exited")

realestate_client = RealEstateClient(config=realestate_config)
realestate_context = RealEstateContext(client=realestate_client, nrg_trade=NRGTradeAPI(realestate_client))
ctx = realestate_context

@asynccontextmanager
async def realestate_lifespan(app: FastMCP):
    logger.info("Initializing RealEstate FastMCP server...")
    try:
        logger.info(f"Server Name: {mcp_config.server_name}")
        logger.info(f"Host: {mcp_config.host}")
        logger.info(f"Port: {mcp_config.port}")
        logger.info(f"Log Level: {mcp_config.log_level}")
        client = RealEstateClient(config=realestate_config)
        ctx = RealEstateContext(client=client, nrg_trade=NRGTradeAPI(client))
        logger.info("RealEstate client and API modules initialized successfully.")
        await asyncio.sleep(0)  # async generator로 인식되도록 보장
        yield ctx
    except Exception as e:
        logger.error(f"Failed to initialize RealEstate client: {e}", exc_info=True)
        raise
    finally:
        logger.info("Shutting down RealEstate FastMCP server...")

tool_registry = initialize_registry()
mcp = FastMCP(
    "KR RealEstate MCP",
    instructions="Korean real estate transaction analysis MCP server.",
    lifespan=realestate_lifespan,
)

for module_name in ["transaction_tools"]:
    importlib.import_module(f"mcp_kr_realestate.tools.{module_name}")

def main():
    logger.info("✅ Initializing RealEstate FastMCP server...")
    transport = mcp_config.transport
    port = mcp_config.port
    if transport == "sse":
        asyncio.run(run_server(transport="sse", port=port))
    else:
        mcp.run()

async def run_server(
    transport: Literal["stdio", "sse"] = "stdio",
    port: int = 8001,
) -> None:
    if transport == "stdio":
        await mcp.run_stdio_async()
    elif transport == "sse":
        logger.info(f"Starting server with SSE transport on http://0.0.0.0:{port}")
        await mcp.run_sse_async(host="0.0.0.0", port=port)

if __name__ == "__main__":
    main() 