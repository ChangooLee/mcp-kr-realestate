"""
레지스트리 초기화
""" 

from mcp_kr_realestate.registry.tool_registry import ToolRegistry

def initialize_registry() -> ToolRegistry:
    registry = ToolRegistry()

    registry.register_tool(
        name="get_nrg_trade_data",
        korean_name="실거래가 XML 다운로드",
        description="상업업무용 부동산 매매 실거래가 API를 호출하여 XML 파일로 저장합니다.",
        parameters={
            "type": "object",
            "properties": {
                "lawd_cd": {"type": "string", "description": "법정동코드 5자리"},
                "deal_ymd": {"type": "string", "description": "거래년월 (YYYYMM)"}
            },
            "required": ["lawd_cd", "deal_ymd"]
        },
        linked_tools=["parse_nrg_trade_xml", "summarize_nrg_trade"]
    )

    registry.register_tool(
        name="get_region_codes",
        korean_name="법정동 코드 전체 조회",
        description="국토교통부 실거래가 API에서 사용하는 전체 법정동 코드를 조회합니다.",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        },
        linked_tools=[]
    )

    registry.register_tool(
        name="parse_nrg_trade_xml",
        korean_name="실거래가 XML 파싱",
        description="저장된 실거래가 XML 파일을 DataFrame으로 파싱합니다.",
        parameters={
            "type": "object",
            "properties": {
                "xml_path": {"type": "string", "description": "XML 파일 경로"}
            },
            "required": ["xml_path"]
        },
        linked_tools=["summarize_nrg_trade"]
    )

    registry.register_tool(
        name="summarize_nrg_trade",
        korean_name="실거래가 통계 요약",
        description="실거래가 DataFrame에서 주요 통계(거래금액, 면적, 층, 건축년도 등)를 요약합니다.",
        parameters={
            "type": "object",
            "properties": {
                "df": {"type": "object", "description": "실거래가 DataFrame"}
            },
            "required": ["df"]
        },
        linked_tools=[]
    )

    return registry 