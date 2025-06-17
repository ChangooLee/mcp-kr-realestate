"""
도구 메타데이터 관리
""" 

import logging
from typing import Dict, List, Optional

logger = logging.getLogger("mcp-kr-realestate")

class ToolMetadata:
    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict,
        korean_name: Optional[str] = None,
        linked_tools: Optional[List[str]] = None
    ):
        self.name = name
        self.korean_name = korean_name
        self.description = description
        self.parameters = parameters
        self.linked_tools = linked_tools or []

    def rich_description(self) -> str:
        lines = []
        if self.korean_name:
            lines.append(f"[도구 이름] {self.korean_name}")
        if self.description:
            lines.append(f"[설명] {self.description}")
        props = self.parameters.get("properties", {})
        required = set(self.parameters.get("required", []))
        if props:
            lines.append("[입력 파라미터]")
            for key, schema in props.items():
                desc = schema.get("description", "")
                mark = " (필수)" if key in required else ""
                lines.append(f"- `{key}`: {desc}{mark}")
        if self.linked_tools:
            links = ", ".join(self.linked_tools)
            lines.append(f"[연관 도구] {links}")
        return "\n".join(lines)

    def to_function_schema(self) -> dict:
        """OpenAI function_call용 포맷 변환"""
        return {
            "name": self.name,
            "description": self.rich_description(),
            "parameters": self.parameters
        }

    def to_mcp_tool(self) -> dict:
        """mcpo가 읽는 MCP list_tools용 포맷"""
        return {
            "name": self.name,
            "description": self.rich_description(),
            "inputSchema": self.parameters
        }

    def brief_summary(self) -> str:
        kor = f" ({self.korean_name})" if self.korean_name else ""
        return f"- {self.name}{kor}: {self.description}"

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, ToolMetadata] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: dict,
        korean_name: Optional[str] = None,
        linked_tools: Optional[List[str]] = None
    ):
        self.tools[name] = ToolMetadata(
            name=name,
            description=description,
            parameters=parameters,
            korean_name=korean_name,
            linked_tools=linked_tools
        )

    def list_tools(self) -> List[dict]:
        """MCP stdio 기반 list_tools 호출 시 사용하는 rich 포맷"""
        return [tool.to_mcp_tool() for tool in self.tools.values()]

    def export_function_schemas(self) -> List[dict]:
        logger.info(f"Exporting function schemas: {self.tools.values()}")
        return [tool.to_function_schema() for tool in self.tools.values()]

    def export_brief_summary(self) -> str:
        return "\n".join(tool.brief_summary() for tool in self.tools.values())

    def get_tool(self, name: str) -> Optional[ToolMetadata]:
        return self.tools.get(name) 