"""
레지스트리 초기화
""" 

from mcp_kr_realestate.registry.tool_registry import ToolRegistry

def initialize_registry() -> ToolRegistry:
    registry = ToolRegistry()

    registry.register_tool(
        name="get_nrg_trade_data",
        korean_name="실거래가 XML 다운로드",
        description="""
이 도구를 사용하기 전에 반드시 먼저 법정동 코드(5자리, lawd_cd)를 조회하고 선택해야 합니다. 법정동 코드는 실거래가 데이터를 조회하는 데 필수입니다.

사용 절차 안내:
1. 먼저 'get_region_codes' 도구를 사용하여 원하는 지역의 법정동 코드(lawd_cd)를 조회하세요.
2. 조회한 lawd_cd(5자리)와 거래년월(deal_ymd, 6자리: YYYYMM)을 본 도구에 입력하여 실거래가 XML 데이터를 조회하세요.

Arguments:
- lawd_cd (str, required): 법정동코드(5자리)
- deal_ymd (str, required): 거래년월(YYYYMM, 6자리)

Returns: 실거래가 XML 데이터가 저장된 파일 경로를 반환합니다.
""",
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

    registry.register_tool(
        name="get_apt_trade_data",
        korean_name="아파트 매매 실거래가 XML 다운로드",
        description="""
이 도구를 사용하기 전에 반드시 먼저 법정동 코드(5자리, lawd_cd)를 조회하고 선택해야 합니다. 법정동 코드는 아파트 실거래가 데이터를 조회하는 데 필수입니다.

사용 절차 안내:
1. 먼저 'get_region_codes' 도구를 사용하여 원하는 지역의 법정동 코드(lawd_cd)를 조회하세요.
2. 조회한 lawd_cd(5자리)와 거래년월(deal_ymd, 6자리: YYYYMM)을 본 도구에 입력하여 아파트 매매 실거래가 XML 데이터를 조회하세요.

Arguments:
- lawd_cd (str, required): 법정동코드(5자리)
- deal_ymd (str, required): 거래년월(YYYYMM, 6자리)

Returns: 아파트 매매 실거래가 XML 데이터가 저장된 파일 경로를 반환합니다.
""",
        parameters={
            "type": "object",
            "properties": {
                "lawd_cd": {"type": "string", "description": "법정동코드 5자리"},
                "deal_ymd": {"type": "string", "description": "거래년월 (YYYYMM)"}
            },
            "required": ["lawd_cd", "deal_ymd"]
        },
        linked_tools=[]
    )

    registry.register_tool(
        name="parse_apt_trade_xml",
        korean_name="아파트 실거래가 XML 파싱",
        description="저장된 아파트 매매 실거래가 XML 파일을 DataFrame으로 파싱하고, 주요 통계(거래건수, 거래금액, 면적, 층, 단지명 등)를 요약합니다.",
        parameters={
            "type": "object",
            "properties": {
                "xml_path": {"type": "string", "description": "XML 파일 경로"}
            },
            "required": ["xml_path"]
        },
        linked_tools=[]
    )

    return registry 