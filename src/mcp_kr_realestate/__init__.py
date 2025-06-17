# src/mcp_kr_realestate/__init__.py 
import importlib
import click
from mcp_kr_realestate.server import mcp

# 도구 모듈 등록 (모든 @mcp.tool decorator)
for module_name in [
    "transaction_tools",
]:
    importlib.import_module(f"mcp_kr_realestate.tools.{module_name}")

@click.command()
def main():
    """부동산 실거래가 MCP 서버를 실행합니다."""
    mcp.run()

if __name__ == "__main__":
    main() 