"""
컨텍스트 헬퍼
"""

import logging
from typing import Any, Callable, Optional
from mcp_kr_realestate.server import ctx

logger = logging.getLogger("mcp-kr-realestate")

def with_context(
    context: Optional[Any],
    tool_name: str,
    fallback_func: Callable[[Any], Any]
) -> Any:
    """
    MCP context를 안전하게 처리하며, fallback으로 전역 컨텍스트 사용.
    Args:
        context: MCPContext or None
        tool_name: 도구명 (로깅용)
        fallback_func: context.nrg_trade.get_something 등 context 의존 로직
    Returns:
        fallback_func 실행 결과
    """
    logger.info(f"📌 Tool: {tool_name} 호출됨")
    if context is not None:
        try:
            result = fallback_func(context.request_context.lifespan_context)
            logger.info("✅ MCP 내부 컨텍스트 사용")
            return result
        except Exception as e:
            logger.warning(f"⚠️ MCPContext 접근 실패: {e}")
    logger.warning("⚠️ Fallback 전역 컨텍스트 사용")
    return fallback_func(ctx) 