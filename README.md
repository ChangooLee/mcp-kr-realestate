# MCP 부동산 투자 분석 서버

![License](https://img.shields.io/github/license/ChangooLee/mcp-kr-realestate)
![GitHub Stars](https://img.shields.io/github/stars/ChangooLee/mcp-kr-realestate)
![GitHub Issues](https://img.shields.io/github/issues/ChangooLee/mcp-kr-realestate)
![GitHub Last Commit](https://img.shields.io/github/last-commit/ChangooLee/mcp-kr-realestate)

한국 부동산 투자 분석을 위한 Model Context Protocol(MCP) 서버입니다. 다양한 공공 API를 통합하여 포괄적인 부동산 투자 분석과 자동화된 보고서 생성을 지원합니다.

**🔗 GitHub Repository**: https://github.com/ChangooLee/mcp-kr-realestate

## 주요 특징

- **🏢 다양한 자산군 분석** - 오피스, 리테일, 물류센터, 주거용 부동산 종합 분석
- **📊 실시간 데이터 연동** - 국토교통부, 한국부동산원 등 공공 API 통합
- **🌍 전국 단위 분석** - 지역별 분산투자 및 포트폴리오 최적화
- **🤖 AI 보고서 생성** - 맞춤형 투자 분석 보고서 자동 생성
- **📈 고급 재무 분석** - DCF, IRR, 민감도 분석 등 전문적 재무 모델링
- **🛡️ 장애 대응 시스템** - API 장애 시 자동 대체 데이터 소스 활용
- **📱 모니터링 대시보드** - 실시간 성능 모니터링 및 알림 시스템

## 🔰 처음 사용하는 분을 위한 5분 퀘스트

### Step 1: API 키 하나만 준비하기
1. https://www.data.go.kr 접속
2. 회원가입 후 "아파트 매매 실거래가" 검색
3. "활용신청" 버튼 클릭하여 API 키 발급 (즉시 발급)

### Step 2: 최소 설정으로 시작
```python
# 가장 간단한 테스트 코드
from PublicDataReader import TransactionPrice

# 여러분의 API 키를 여기에 입력하세요
api_key = "여기에_발급받은_API키_입력"
api = TransactionPrice(service_key=api_key)

# 강남구 아파트 매매 실거래가 조회 (지난달 기준)
df = api.read_data(
    prod="아파트", 
    trans="매매", 
    sigunguCode="11680",  # 강남구
    yearMonth="202405"    # 2024년 5월
)

print(f"총 {len(df)}건의 거래 데이터를 가져왔습니다!")
print(df.head())
```

### Step 3: 결과 확인
- 오류 없이 실행되면 성공! 🎉
- 오류가 나면 아래 FAQ 섹션 확인

## 자주 묻는 질문 (FAQ)

**Q: "SERVICE_KEY_IS_NOT_REGISTERED_ERROR" 오류가 나요**
A: API 키가 잘못되었거나 아직 활성화되지 않았습니다. 발급 후 1-2시간 후 재시도해보세요.

**Q: "REQUEST_QUOTA_EXCEEDED" 오류가 나요**
A: 일일 호출 한도(1,000건)를 초과했습니다. 내일 다시 시도하거나 운영 계정을 신청하세요.

**Q: 데이터가 너무 적게 나와요**
A: 해당 지역/시기에 거래가 적을 수 있습니다. 다른 지역이나 시기로 테스트해보세요.

## 사용 예시

AI 어시스턴트에게 다음과 같은 요청을 할 수 있습니다:

- **🏢 시장 분석** - "서울 강남구 오피스 시장의 최근 3년간 임대료 추이를 분석해주세요"
- **📊 포트폴리오 구성** - "수도권과 지방을 7:3으로, 오피스와 물류센터를 5:5로 구성한 포트폴리오를 제안해주세요"
- **💰 투자 분석** - "목표 수익률 8%로 5년 보유 예정인 부동산 투자안을 DCF로 분석해주세요"
- **⚠️ 리스크 분석** - "금리 상승 시나리오에서 포트폴리오의 위험도를 평가해주세요"

## 지원 API 및 데이터 소스 (2025년 현재)

### 국토교통부 실거래가 API (세부 분류별)

| 부동산 유형 | 거래 유형 | API URL | 공공데이터포털 ID | 지원 상태 |
|------------|----------|---------|------------------|----------|
| **아파트** | 매매 | `http://openapi.molit.go.kr:8081/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/getRTMSDataSvcAptTrade` | 15058747 | ✅ |
| **아파트** | 매매 상세 | `http://openapi.molit.go.kr/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/getRTMSDataSvcAptTradeDev` | 15057511 | ✅ |
| **아파트** | 전월세 | `http://openapi.molit.go.kr:8081/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/getRTMSDataSvcAptRent` | 15058017 | ✅ |
| **오피스텔** | 매매 | `http://openapi.molit.go.kr/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/getRTMSDataSvcOffiTrade` | 15058452 | ✅ |
| **오피스텔** | 전월세 | `http://openapi.molit.go.kr/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/getRTMSDataSvcOffiRent` | 15058453 | ✅ |
| **연립다세대** | 매매 | `http://openapi.molit.go.kr:8081/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/getRTMSDataSvcRHTrade` | 15058022 | ✅ |
| **연립다세대** | 전월세 | `http://openapi.molit.go.kr:8081/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/getRTMSDataSvcRHRent` | 15058016 | ✅ |
| **단독다가구** | 매매 | `http://openapi.molit.go.kr:8081/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/getRTMSDataSvcSHTrade` | 15058023 | ✅ |
| **단독다가구** | 전월세 | `http://openapi.molit.go.kr:8081/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/getRTMSDataSvcSHRent` | 15058018 | ✅ |
| **토지** | 매매 | `http://apis.data.go.kr/1613000/RTMSDataSvcLandTrade/getRTMSDataSvcLandTrade` | 15126466 | ✅ |
| **상업업무용** | 매매 | `http://openapi.molit.go.kr/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/getRTMSDataSvcNrgTrade` | 15057267 | ✅ |
| **분양입주권** | 매매 | `http://openapi.molit.go.kr:8081/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/getRTMSDataSvcSilvTrade` | 15058024 | ✅ |

### 기타 주요 API (2025년 6월 업데이트)

| API 서비스 | 제공 기관 | API URL | 주요 데이터 | 공공데이터포털 ID | 지원 상태 |
|-----------|-----------|---------|-------------|------------------|----------|
| **건축물대장정보** | 국토교통부 | `https://apis.data.go.kr/1613000/BldRgstService_v2/` | 건물 용도, 면적, 구조 정보 | 15044713 | ⚠️ 변경됨 |
| **건축HUB 건축물대장** | 국토교통부 | `https://www.hub.go.kr/portal/psg/idx-intro-openApi.do` | 건축물대장 통합 정보 | 15134735 | ✅ 신규 |
| **인허가 및 공급정보** | 국토교통부 | `https://www.hub.go.kr/portal/psg/idx-intro-openApi.do` | 건축인허가, 주택공급 통계 | - | ✅ 지원 |
| **토지/소유 정보** | 국토교통부 | `http://openapi.molit.go.kr/OpenAPI_ToolInstallPackage/service/rest/LandInfoService/` | 지목, 면적, 개별공시지가 | - | ✅ 지원 |
| **부동산 종합정보** | 한국부동산원 | `https://www.reb.or.kr/r-one/openapi/` | 가격지수, 전세가율, 미분양 현황 | 15134761 | ✅ 지원 |
| **서울 열린데이터** | 서울특별시 | `http://openAPI.seoul.go.kr:8088/{API_KEY}/xml/{SERVICE_NAME}/` | 서울시 부동산 및 도시 데이터 | - | ✅ 지원 |
| **공공주택 정보** | LH공사 | `https://www.data.go.kr/data/15083046/openapi.do` | 공공임대주택, 분양 정보 | 15083046 | ✅ 지원 |
| **상가/상권 정보** | 소상공인진흥공단 | `https://www.data.go.kr/data/15012005/openapi.do` | 임대료, 권리금, 상권 통계 | 15012005 | ⚠️ 2025년 변경 |
| **공매 물건 정보** | 한국자산관리공사 | `https://www.onbid.co.kr/openapi/` | 경매/공매 매물 정보 | - | ✅ 지원 |
| **국가통계** | 통계청 KOSIS | `https://kosis.kr/openapi/` | 인구, 경제 통계 | 15056860 | ✅ 지원 |
| **경제지표** | 한국은행 ECOS | `https://ecos.bok.or.kr/api/` | 금리, 물가, GDP 등 거시지표 | - | ✅ 지원 |

> **⚠️ 2025년 주요 변경사항**
> 
> 1. **건축물대장 API**: 기존 API가 건축HUB 시스템으로 통합 이전됨
> 2. **소상공인진흥공단 API**: 상권업종분류가 837개 → 247개로 개편, 상가업소번호 체계 변경
> 3. **공공데이터포털 ID**: 최신 ID로 업데이트 완료

## 빠른 시작 가이드

### 1. API 키 설정

다음 API 키들을 준비하세요:

#### 필수 API 키

1. **공공데이터포털** (data.go.kr)
   - 회원가입: https://www.data.go.kr
   - 대부분의 국토교통부, 한국부동산원 API 접근 가능
   - 개발계정: 1,000건/일, 운영계정: 활용사례 등록 후 무제한

2. **한국은행 ECOS** (ecos.bok.or.kr)
   - 회원가입: https://ecos.bok.or.kr
   - 경제통계 데이터 접근용 API 키
   - 10,000건/일, 즉시 발급

3. **서울 열린데이터광장** (data.seoul.go.kr)
   - 회원가입: https://data.seoul.go.kr
   - 서울시 데이터 접근용 API 키
   - 1,000건/일, 즉시 발급

#### 선택 API 키

4. **KOSIS 통계청** (kosis.kr)
   - 회원가입: https://kosis.kr/openapi/
   - 국가통계 접근용
   - 10,000건/일

### 2. 설치

```bash
# 저장소 복제
git clone https://github.com/ChangooLee/mcp-kr-realestate.git
cd mcp-kr-realestate

# Python 3.10 이상 필요
python3 --version

# 가상 환경 생성
python3.10 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 의존성 설치
pip install --upgrade pip
pip install -e .
```

### 3. 환경 변수 설정

`.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
# =================================================================
# 필수 API 키 - 이 키들은 반드시 설정해야 합니다
# =================================================================

# 공공데이터포털 API 키 (필수)
# 발급처: https://www.data.go.kr
# 용도: 국토교통부 실거래가, 건축물대장 등 대부분 API
PUBLIC_DATA_API_KEY=your_public_data_api_key_here

# 한국은행 ECOS API 키 (필수)
# 발급처: https://ecos.bok.or.kr
# 용도: 금리, 환율, 경제지표 등
ECOS_API_KEY=your_ecos_api_key_here

# =================================================================
# 선택 API 키 - 특정 지역/기능 사용 시에만 필요
# =================================================================

# 서울시 열린데이터 API 키 (서울 데이터 사용 시)
# 발급처: https://data.seoul.go.kr
SEOUL_DATA_API_KEY=your_seoul_data_api_key_here

# KOSIS 통계청 API 키 (국가통계 사용 시)
# 발급처: https://kosis.kr/openapi/
KOSIS_API_KEY=your_kosis_api_key_here

# =================================================================
# 서버 설정
# =================================================================
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
TRANSPORT=stdio

# =================================================================
# 고급 설정 (필요 시 수정)
# =================================================================

# API 호출 간격 (초) - 너무 빠르면 제한될 수 있음
API_CALL_INTERVAL=0.1

# 재시도 횟수
MAX_RETRIES=3

# 타임아웃 설정 (초)
REQUEST_TIMEOUT=30

# 데이터 캐시 보관 기간 (일)
CACHE_RETENTION_DAYS=30

# 성능 모니터링 활성화
ENABLE_PERFORMANCE_MONITORING=true

# 알림 설정 (Slack 웹훅 URL)
SLACK_WEBHOOK_URL=your_slack_webhook_url_here
```

## Claude Desktop 통합

### 설정 방법

1. Claude Desktop에서 햄버거 메뉴(☰) > Settings > Developer > "Edit Config" 클릭
2. 다음 설정을 추가:

```json
{
  "mcpServers": {
    "kr-real-estate-analysis": {
      "command": "/path/to/your/project/.venv/bin/mcp-kr-realestate",
      "env": {
        "PUBLIC_DATA_API_KEY": "your_public_data_api_key",
        "SEOUL_DATA_API_KEY": "your_seoul_data_api_key",
        "ECOS_API_KEY": "your_ecos_api_key",
        "KOSIS_API_KEY": "your_kosis_api_key",
        "HOST": "0.0.0.0",
        "PORT": "8000",
        "TRANSPORT": "stdio",
        "LOG_LEVEL": "INFO",
        "ENABLE_PERFORMANCE_MONITORING": "true"
      }
    }
  }
}
```

## 주요 도구 및 기능

### 시장 분석 도구

- `get_transaction_data`: 부동산 실거래가 조회
- `get_building_info`: 건축물 대장 정보 조회
- `get_market_index`: 부동산 시장 지수 분석
- `get_supply_data`: 공급 및 인허가 현황 분석

#### get_transaction_data 함수 사용 예시

```python
# 입력 예시
input_params = {
    "asset_type": "아파트",
    "transaction_type": "매매",
    "region_code": "11680",  # 강남구
    "year_month": "202406",
    "detailed": True
}

# 출력 예시 (DataFrame)
output_sample = pd.DataFrame({
    "거래금액": ["230,000", "195,000", "178,000"],
    "아파트": ["래미안강남", "타워팰리스", "트럼프타워"],
    "전용면적": [84.91, 59.98, 72.45],
    "층": [15, 8, 23],
    "건축년도": [2021, 2004, 2018],
    "거래년월일": ["2024-06-15", "2024-06-08", "2024-06-22"]
})

# 주요 필드 설명
response_fields = {
    "거래금액": "매매 가격 (만원 단위, 쉼표 포함)",
    "건축년도": "준공년도 (YYYY 형식)",
    "년": "거래년도",
    "월": "거래월",
    "일": "거래일",
    "아파트": "아파트명",
    "전용면적": "전용면적(㎡)",
    "지번": "지번",
    "지역코드": "법정동코드",
    "층": "해당층",
    "해제사유발생일": "해제사유발생일 (해제된 경우)",
    "해제여부": "거래 해제 여부"
}
```

### 포트폴리오 분석 도구

- `create_portfolio`: 맞춤형 포트폴리오 구성
- `analyze_diversification`: 지역/자산군 분산효과 분석
- `calculate_portfolio_risk`: 포트폴리오 위험도 측정
- `optimize_allocation`: 최적 자산 배분 제안

#### create_portfolio 함수 사용 예시

```python
# 입력 컨텍스트
portfolio_context = {
    "target_return": 0.08,
    "risk_tolerance": "중간",
    "investment_amount": 10000000000,  # 100억원
    "regions": ["서울", "경기", "부산"],
    "asset_types": ["오피스", "물류센터", "주거"],
    "allocation_strategy": "균등분산"
}

# 출력 예시
portfolio_output = {
    "recommended_allocation": {
        "오피스": {"weight": 0.4, "amount": 4000000000, "regions": {"서울": 0.6, "경기": 0.4}},
        "물류센터": {"weight": 0.35, "amount": 3500000000, "regions": {"경기": 0.5, "부산": 0.5}},
        "주거": {"weight": 0.25, "amount": 2500000000, "regions": {"서울": 0.8, "경기": 0.2}}
    },
    "expected_return": 0.082,
    "risk_metrics": {
        "volatility": 0.156,
        "sharpe_ratio": 0.385,
        "max_drawdown": 0.234
    },
    "diversification_score": 0.78
}
```

### 재무 분석 도구

- `dcf_analysis`: 현금흐름할인법 분석
- `irr_calculation`: 내부수익률 계산
- `sensitivity_analysis`: 민감도 분석
- `scenario_modeling`: 시나리오별 수익률 모델링

### 리스크 분석 도구

- `vacancy_risk_analysis`: 공실률 위험 분석
- `interest_rate_sensitivity`: 금리 민감도 분석
- `macro_economic_impact`: 거시경제 영향 분석
- `stress_testing`: 스트레스 테스트

### 보고서 생성 도구

- `generate_investment_report`: 투자 분석 보고서 생성
- `create_market_overview`: 시장 현황 보고서 작성
- `portfolio_performance_report`: 포트폴리오 성과 보고서
- `risk_assessment_report`: 위험 평가 보고서

## MCP 컨텍스트 스키마

### 투자 분석 컨텍스트 예시

```json
{
  "analysis_context": {
    "purpose": "안정적인 임대수익 확보 및 장기 자본성장",
    "asset_types": ["오피스", "물류센터", "주거"],
    "region": "전국 (주요 광역시 중심)",
    "investment_horizon": 7,
    "target_return": 0.07,
    "risk_tolerance": "중간",
    "leverage_ratio": 0.5,
    "special_conditions": [
      "분기별 현금흐름 재투자",
      "ESG 고려 투자"
    ]
  }
}
```

### 주요 파라미터

| 파라미터 | 설명 | 예시 값 |
|---------|------|---------|
| `purpose` | 투자 목적 | "안정적 임대수익", "공격적 성장" |
| `asset_types` | 자산 유형 | ["오피스", "리테일", "물류", "주거"] |
| `region` | 투자 지역 | "수도권", "전국", "5대 광역시" |
| `investment_horizon` | 투자 기간(년) | 5, 7, 10 |
| `target_return` | 목표 수익률 | 0.06, 0.08, 0.12 |
| `risk_tolerance` | 위험 허용도 | "낮음", "중간", "높음" |
| `leverage_ratio` | 레버리지 비율 | 0.5, 0.6, 0.7 |

## API 연동 상세 가이드

### 주요 API 엔드포인트

#### 1. 국토교통부 실거래가 API (12개 세부 API)

**기본 사용법:**
```python
from PublicDataReader import TransactionPrice

service_key = "YOUR_SERVICE_KEY"
api = TransactionPrice(service_key=service_key)

# 아파트 매매 실거래가 조회
df = api.get_data(
    property_type="아파트", 
    trade_type="매매", 
    sigungu_code="11680",  # 강남구
    year_month="202406"
)
```

**전체 부동산 유형별 API:**

| 부동산 유형 | 거래 유형 | 공공데이터포털 API ID | 서비스 명 |
|------------|----------|---------------------|----------|
| 아파트 | 매매 | 15058747 | getRTMSDataSvcAptTrade |
| 아파트 | 매매 상세 | 15057511 | getRTMSDataSvcAptTradeDev |
| 아파트 | 전월세 | 15058017 | getRTMSDataSvcAptRent |
| 오피스텔 | 매매 | 15058452 | getRTMSDataSvcOffiTrade |
| 오피스텔 | 전월세 | 15058453 | getRTMSDataSvcOffiRent |
| 연립다세대 | 매매 | 15058022 | getRTMSDataSvcRHTrade |
| 연립다세대 | 전월세 | 15058016 | getRTMSDataSvcRHRent |
| 단독다가구 | 매매 | 15058023 | getRTMSDataSvcSHTrade |
| 단독다가구 | 전월세 | 15058018 | getRTMSDataSvcSHRent |
| 토지 | 매매 | 15126466 | getRTMSDataSvcLandTrade |
| 상업업무용 | 매매 | 15057267 | getRTMSDataSvcNrgTrade |
| 분양입주권 | 매매 | 15058024 | getRTMSDataSvcSilvTrade |

**직접 API 호출 예시:**
```python
import requests
import xml.etree.ElementTree as ET

def get_apt_trade_data(service_key, lawd_cd, deal_ymd):
    url = "http://openapi.molit.go.kr:8081/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/getRTMSDataSvcAptTrade"
    params = {
        'serviceKey': service_key,
        'LAWD_CD': lawd_cd,  # 법정동코드 5자리 (예: 11680 - 강남구)
        'DEAL_YMD': deal_ymd  # 거래년월 (예: 202406)
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        items = []
        for item in root.findall(".//item"):
            data = {}
            for child in item:
                data[child.tag] = child.text
            items.append(data)
        return items
    else:
        return None

# 사용 예시
data = get_apt_trade_data("YOUR_API_KEY", "11680", "202406")
```

#### 2. 건축물대장 API (⚠️ 2025년 업데이트)

> **중요**: 2025년부터 기존 건축물대장 API가 건축HUB 시스템으로 통합되었습니다.

**신규 건축HUB API 사용법:**
```python
from PublicDataReader import BuildingLedger

service_key = "YOUR_SERVICE_KEY"
api = BuildingLedger(service_key)

# 기본개요 조회
df = api.get_data(
    ledger_type="기본개요",  # 기본개요, 총괄표제부, 표제부, 층별개요 등
    sigungu_code="41135",   # 시군구코드
    bdong_code="11000",     # 법정동코드
    bun="542",              # 번지
    ji=""                   # 지번
)
```

**건축HUB API 응답 예시:**
```json
{
  "response": {
    "header": {
      "resultCode": "00",
      "resultMsg": "NORMAL_SERVICE"
    },
    "body": {
      "items": [
        {
          "platPlc": "서울특별시 강남구 역삼동 123-45",
          "sigunguCd": "11680",
          "bjdongCd": "10300",
          "platGbCd": "0",
          "bun": "123",
          "ji": "45",
          "mgmBldrgstPk": "11680-100123456",
          "bldNm": "강남빌딩",
          "splotNm": "역삼동123-45",
          "block": "",
          "lot": "",
          "bylotCnt": "0",
          "naRoadCd": "116804163",
          "naBjdongCd": "10300",
          "naUgrndCd": "0",
          "naMainBun": "123",
          "naSubBun": "45"
        }
      ],
      "numOfRows": 10,
      "pageNo": 1,
      "totalCount": 1
    }
  }
}
```

**건축HUB API 엔드포인트:**
- 기본개요: `https://www.hub.go.kr/portal/psg/openapi/getBldgInfo`
- 총괄표제부: `https://www.hub.go.kr/portal/psg/openapi/getBldgSummary`
- 표제부: `https://www.hub.go.kr/portal/psg/openapi/getBldgTitle`
- 층별개요: `https://www.hub.go.kr/portal/psg/openapi/getBldgFloor`

#### 3. 한국은행 ECOS API

```python
import requests

# 주요 경제지표 조회
def get_ecos_data(api_key, stat_code, period_start, period_end):
    url = f"https://ecos.bok.or.kr/api/StatisticSearch/{api_key}/json/kr/1/100/{stat_code}/M/{period_start}/{period_end}"
    response = requests.get(url)
    return response.json()

# 기준금리 조회
interest_rate = get_ecos_data("YOUR_API_KEY", "722Y001", "202301", "202406")

# 환율 조회 (원/달러)
exchange_rate = get_ecos_data("YOUR_API_KEY", "731Y001", "20240101", "20250631")
```

**주요 ECOS 통계 코드:**
- 기준금리: `722Y001`
- 환율(원/달러): `731Y001`
- 소비자물가지수: `901Y009`
- GDP: `200Y001`
- 콜금리: `722Y002`
- 회사채수익률(3년AA-): `817Y002`
- 가계대출금리: `722Y003`
- 주택담보대출금리: `722Y004`

#### 4. 서울시 열린데이터광장 API

```python
import requests

def get_seoul_data(api_key, service_name, start_idx=1, end_idx=100):
    url = f"http://openAPI.seoul.go.kr:8088/{api_key}/json/{service_name}/{start_idx}/{end_idx}/"
    response = requests.get(url)
    return response.json()

# 서울시 부동산 실거래가 조회
real_estate_data = get_seoul_data("YOUR_API_KEY", "StatsRealEstatePrice")

# 서울시 인구 통계 조회
population_data = get_seoul_data("YOUR_API_KEY", "SeoulPopulationStats")
```

**주요 서울시 서비스:**
- 부동산 실거래가: `StatsRealEstatePrice`
- 지가변동률: `LandPriceVariationRate`
- 인구통계: `SeoulPopulationStats`
- 대기환경정보: `RealtimeCityAir`
- 상권분석정보: `VwsmSignguStorW`
- 전월세 거래정보: `tbLnOpendataRentV`

#### 5. KOSIS 통계청 API

```python
import requests

def get_kosis_data(api_key, tbl_id, obj_l1="ALL", obj_l2="", itm_id=""):
    url = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
    params = {
        'method': 'getList',
        'apiKey': api_key,
        'tblId': tbl_id,
        'objL1': obj_l1,
        'objL2': obj_l2,
        'itmId': itm_id,
        'format': 'json',
        'jsonVD': 'Y'
    }
    response = requests.get(url, params=params)
    return response.json()

# 인구 통계 조회
population_stats = get_kosis_data("YOUR_API_KEY", "DT_1B04005N", "ALL", "", "13103042901T_1T2+")
```

#### 6. 소상공인진흥공단 상권정보 API (⚠️ 2025년 대규모 변경)

> **중요**: 2025년 상권업종분류가 837개 → 247개로 개편되었습니다.

```python
from PublicDataReader import SmallShop

service_key = "YOUR_SERVICE_KEY"
api = SmallShop(service_key)

# 반경 내 상가업소 조회
df = api.get_data(
    service_name="반경상권",
    cx=127.042325940821,  # 경도
    cy=37.5272105674053,  # 위도
    radius=500            # 반경(m)
)

# 사각형 영역 상가업소 조회
df = api.get_data(
    service_name="사각형상권",
    minx=127.0327683531071,
    miny=37.495967935149146,
    maxx=127.04268179746694,
    maxy=37.502402894207286
)
```

**2025년 변경사항:**
- 상권업종분류: 표준산업분류 기반으로 개편
- 업종분류 체계: 대분류(10개), 중분류(75개), 소분류(247개)
- 표준산업분류: 9차 → 10차
- 상가업소번호: 새롭게 생성 (과거 데이터와 연계 불가)

#### 7. 한국부동산원 R-ONE API

```python
import requests

def get_reb_statistics(api_key, service_code, region_code="", period=""):
    base_url = "https://www.reb.or.kr/r-one/openapi/"
    url = f"{base_url}{service_code}"
    params = {
        'KEY': api_key,
        'Type': 'json',
        'pIndex': 1,
        'pSize': 100
    }
    if region_code:
        params['AREA_CD'] = region_code
    if period:
        params['YM'] = period
    
    response = requests.get(url, params=params)
    return response.json()

# 주택가격동향 조회
housing_price = get_reb_statistics("YOUR_API_KEY", "getPriceIndex", "1100", "202406")

# 전세가격동향 조회  
jeonse_price = get_reb_statistics("YOUR_API_KEY", "getJeonseIndex", "1100", "202406")
```

### API 인증 키 발급 방법

#### 공공데이터포털 (data.go.kr)
1. **회원가입**: https://www.data.go.kr 접속 후 회원가입
2. **API 검색**: 원하는 API 서비스 검색 (예: "국토교통부 아파트 매매")
3. **활용신청**: "활용신청" 버튼 클릭
4. **신청서 작성**: 
   - 활용목적: "부동산 투자 분석 서비스 개발"
   - 기간: 1년 (갱신 가능)
   - 개발계정: 즉시 발급 (1,000건/일)
   - 운영계정: 활용사례 등록 후 승인 (무제한)

#### 한국은행 ECOS (ecos.bok.or.kr)
1. **회원가입**: https://ecos.bok.or.kr 접속
2. **Open API 메뉴**: 상단 메뉴에서 "Open API" 선택
3. **인증키 신청**: "인증키 신청" 버튼 클릭
4. **즉시 발급**: 신청 즉시 API 키 발급 (10,000건/일)

#### 서울시 열린데이터광장 (data.seoul.go.kr)
1. **회원가입**: https://data.seoul.go.kr 접속
2. **Open API**: "Open API" → "인증키 신청" 메뉴
3. **신청**: 용도 기재 후 신청
4. **즉시 발급**: 개발용 키 즉시 발급 (1,000건/일)

#### KOSIS 통계청 (kosis.kr)
1. **회원가입**: https://kosis.kr 접속 후 회원가입
2. **공유서비스**: "공유서비스" → "OpenAPI" 메뉴
3. **인증키 신청**: 활용 목적 기재
4. **발급**: 1일 내 인증키 발급 (10,000건/일)

### API 호출 제한 및 주의사항

| API 서비스 | 일일 호출 한도 | 초당 호출 제한 | 추가 제한사항 | 신청 방법 |
|-----------|---------------|---------------|---------------|----------|
| **국토교통부 실거래가** | 개발: 1,000 / 운영: 무제한 | 10회/초 | 월별 조회만 가능, LAWD_CD 5자리 필수 | 공공데이터포털 |
| **건축HUB (신규)** | 개발: 10,000 / 운영: 무제한 | 10회/초 | 시군구코드, 법정동코드, 번지 필수 | 공공데이터포털 |
| **한국은행 ECOS** | 10,000회 | 100회/분 | 통계표별 코드 체계 상이 | ECOS 직접 신청 |
| **서울시 열린데이터** | 개발: 1,000 / 운영: 협의 | 5회/초 | 서울시 지역만 제공 | 서울시 직접 신청 |
| **KOSIS 통계청** | 10,000회 | 제한 없음 | 대용량 조회 시 응답 지연 | KOSIS 직접 신청 |
| **소상공인진흥공단** | 개발: 1,000 / 운영: 100,000 | 10회/초 | 2025년 데이터 구조 변경 | 공공데이터포털 |
| **한국부동산원** | 협의 | 제한 없음 | 통계 발표 일정에 따라 업데이트 | 직접 문의 |

### 실제 공공데이터포털 API ID 참조표

| API 명 | 데이터포털 ID | 제공기관 | 승인 방식 | 변경사항 |
|--------|---------------|----------|----------|----------|
| 아파트 매매 실거래가 | 15058747 | 국토교통부 | 자동승인 | - |
| 아파트 매매 실거래가 상세 | 15057511 | 국토교통부 | 자동승인 | - |
| 아파트 전월세 자료 | 15058017 | 국토교통부 | 자동승인 | - |
| 오피스텔 매매 신고 | 15058452 | 국토교통부 | 자동승인 | - |
| 오피스텔 전월세 자료 | 15058453 | 국토교통부 | 자동승인 | - |
| 연립다세대 매매 | 15058022 | 국토교통부 | 자동승인 | - |
| 연립다세대 전월세 | 15058016 | 국토교통부 | 자동승인 | - |
| 단독다가구 매매 | 15058023 | 국토교통부 | 자동승인 | - |
| 단독다가구 전월세 | 15058018 | 국토교통부 | 자동승인 | - |
| 토지 매매 실거래가 | 15126466 | 국토교통부 | 자동승인 | - |
| 상업업무용 부동산 매매 | 15057267 | 국토교통부 | 자동승인 | - |
| 건축HUB 건축물대장정보 | 15134735 | 국토교통부 | 자동승인 | **신규** |
| 상가(상권)정보 | 15012005 | 소상공인진흥공단 | 자동승인 | **2025년 변경** |
| 부동산통계 조회 서비스 | 15134761 | 한국부동산원 | 자동승인 | - |

### 법정동코드 및 지역코드 활용 가이드

**법정동코드 (LAWD_CD) 사용법:**
- 5자리 코드 사용 (예: 서울 강남구 = 11680)
- 전체 코드 확인: https://www.code.go.kr/stdcode/regCodeL.do

**주요 지역 법정동코드:**
```python
# 서울특별시 주요 구
seoul_codes = {
    "종로구": "11110", "중구": "11140", "용산구": "11170",
    "성동구": "11200", "광진구": "11215", "동대문구": "11230",
    "중랑구": "11260", "성북구": "11290", "강북구": "11305",
    "도봉구": "11320", "노원구": "11350", "은평구": "11380",
    "서대문구": "11410", "마포구": "11440", "양천구": "11470",
    "강서구": "11500", "구로구": "11530", "금천구": "11545",
    "영등포구": "11560", "동작구": "11590", "관악구": "11620",
    "서초구": "11650", "강남구": "11680", "송파구": "11710",
    "강동구": "11740"
}

# 경기도 주요 시
gyeonggi_codes = {
    "수원시": "41111", "성남시": "41131", "고양시": "41281",
    "용인시": "41461", "안양시": "41171", "안산시": "41271",
    "부천시": "41191", "의정부시": "41150", "광명시": "41210",
    "평택시": "41220", "시흥시": "41390", "김포시": "41570",
    "화성시": "41590", "광주시": "41610", "양주시": "41630"
}
```

### 데이터 수집 최적화 전략

#### 1. 배치 처리 및 캐싱
```python
import time
from datetime import datetime, timedelta
import pandas as pd

def collect_transaction_data_batch(regions, months):
    """여러 지역, 여러 월의 실거래가 데이터를 배치로 수집"""
    all_data = []
    
    for region in regions:
        for month in months:
            try:
                # API 호출 제한 준수
                time.sleep(0.1)  
                
                df = api.read_data(
                    prod="아파트",
                    trans="매매", 
                    sigunguCode=region,
                    yearMonth=month
                )
                all_data.append(df)
                
            except Exception as e:
                print(f"Error for {region}-{month}: {e}")
                continue
    
    return pd.concat(all_data, ignore_index=True)
```

#### 2. 에러 처리 및 재시도
```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_robust_session():
    """안정적인 HTTP 세션 생성"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session
```

#### 3. 병렬 처리
```python
import concurrent.futures
from functools import partial

def parallel_api_calls(api_function, param_list, max_workers=5):
    """병렬로 API 호출 수행"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(api_function, param_list))
    return results
```

## 자동화 파이프라인

시스템은 다음과 같은 자동화된 분석 파이프라인을 제공합니다:

1. **MCP 입력** → 사용자 투자 조건 및 선호도 수집
2. **데이터 수집** → 관련 API로부터 실시간 데이터 수집
3. **데이터 전처리** → 데이터 정제 및 통합
4. **투자 분석** → DCF, IRR, 포트폴리오 최적화 등 수행
5. **보고서 생성** → AI를 활용한 맞춤형 분석 보고서 작성

## 분석 프레임워크

### 재무 분석
- **현금흐름할인법(DCF)**: 미래 현금흐름 할인을 통한 내재가치 평가
- **내부수익률(IRR)**: 투자 수익률 계산 및 목표 대비 평가
- **민감도 분석**: 주요 변수 변화에 따른 수익률 영향 분석

### 시장 분석
- **공실률 분석**: 지역별 공실률 추이 및 임대시장 건전성 평가
- **임대료 분석**: 과거 임대료 상승률 및 미래 전망 분석
- **거래량 분석**: 시장 활성도 및 유동성 평가

### 위험 관리
- **지역 분산**: 지리적 분산을 통한 지역 위험 완화
- **자산군 분산**: 다양한 부동산 유형 조합으로 위험 분산
- **거시경제 분석**: 금리, 물가 등 외부 요인 영향 평가

## API 사용 예시

### PublicDataReader 활용

```python
from PublicDataReader import TransactionPrice

# 국토교통부 실거래가 API 사용
service_key = "YOUR_SERVICE_KEY"
api = TransactionPrice(service_key=service_key)

# 서울 강남구 아파트 매매 실거래 조회
df = api.read_data(
    prod="아파트", 
    trans="매매", 
    sigunguCode="11680",  # 강남구 코드
    yearMonth="202406"
)
```

## 장애 대응 및 데이터 관리

### API 장애 대응 시스템

```python
class DataSourceManager:
    """데이터 소스 관리 및 장애 대응"""
    
    def __init__(self):
        self.primary_sources = ["공공데이터포털", "한국부동산원"]
        self.fallback_sources = ["캐시데이터", "과거데이터"]
        self.cache_retention_days = 30
    
    def get_data_with_fallback(self, data_type, params):
        """주 데이터 소스 실패 시 대체 소스 활용"""
        
        # 1차: 실시간 API 호출
        try:
            return self.call_primary_api(data_type, params)
        except APIException as e:
            logging.warning(f"Primary API failed: {e}")
        
        # 2차: 캐시 데이터 활용
        try:
            cached_data = self.get_cached_data(data_type, params)
            if self.is_cache_valid(cached_data):
                logging.info("Using cached data due to API failure")
                return cached_data
        except CacheException as e:
            logging.warning(f"Cache access failed: {e}")
        
        # 3차: 과거 동월 데이터 활용
        try:
            historical_data = self.get_historical_data(data_type, params)
            logging.info("Using historical data as last resort")
            return historical_data
        except Exception as e:
            logging.error(f"All data sources failed: {e}")
            raise DataUnavailableException("모든 데이터 소스에서 데이터를 가져올 수 없습니다")
```

### API별 장애 대응 전략

| API 서비스 | 장애 감지 방법 | 1차 대응 | 2차 대응 | 3차 대응 |
|-----------|---------------|----------|----------|----------|
| 국토교통부 실거래가 | HTTP 500/503 | 30초 후 재시도 | 캐시 데이터 활용 | 전월 데이터 활용 |
| 건축HUB | 응답 지연 | 타임아웃 후 재시도 | 기존 건축물대장 API | 공공데이터포털 검색 |
| 한국은행 ECOS | 인증 오류 | API 키 재검증 | 대체 경제지표 | 고정값 적용 |
| 서울시 열린데이터 | 일일 한도 초과 | 다음날 재시도 | 국토부 데이터 활용 | 추정치 계산 |

### 데이터 관리 정책

```python
class DataPrivacyManager:
    """데이터 프라이버시 관리"""
    
    # 개인정보 포함 가능 데이터 유형
    SENSITIVE_DATA_TYPES = [
        "individual_transaction",  # 개별 거래 정보
        "owner_information",       # 소유자 정보
        "detailed_building_info"   # 상세 건물 정보
    ]
    
    # 데이터 보관 기간
    RETENTION_POLICY = {
        "transaction_data": 365,      # 거래 데이터: 1년
        "market_analysis": 90,        # 시장 분석: 3개월
        "user_portfolio": 30,         # 사용자 포트폴리오: 1개월
        "api_logs": 7                 # API 로그: 1주일
    }
    
    def anonymize_sensitive_data(self, data):
        """민감 정보 익명화"""
        if isinstance(data, dict):
            # 개인정보 마스킹
            if 'owner_name' in data:
                data['owner_name'] = self.mask_name(data['owner_name'])
            if 'phone_number' in data:
                data['phone_number'] = self.mask_phone(data['phone_number'])
        
        return data
    
    def schedule_data_cleanup(self):
        """데이터 자동 정리 스케줄링"""
        for data_type, retention_days in self.RETENTION_POLICY.items():
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            self.delete_old_data(data_type, cutoff_date)
```

## 성능 모니터링

### API 성능 모니터링 시스템

```python
import time
from functools import wraps
from collections import defaultdict

class APIPerformanceMonitor:
    """API 성능 모니터링"""
    
    def __init__(self):
        self.call_stats = defaultdict(list)
        self.error_stats = defaultdict(int)
    
    def monitor_api_call(self, api_name):
        """API 호출 성능 모니터링 데코레이터"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    success = True
                    error_type = None
                except Exception as e:
                    success = False
                    error_type = type(e).__name__
                    raise
                finally:
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    # 성능 통계 수집
                    self.call_stats[api_name].append({
                        'duration': duration,
                        'success': success,
                        'timestamp': start_time,
                        'error_type': error_type
                    })
                    
                    if not success:
                        self.error_stats[f"{api_name}_{error_type}"] += 1
                
                return result
            return wrapper
        return decorator
    
    def get_performance_report(self, api_name=None):
        """성능 리포트 생성"""
        if api_name:
            stats = self.call_stats.get(api_name, [])
        else:
            stats = []
            for calls in self.call_stats.values():
                stats.extend(calls)
        
        if not stats:
            return "No performance data available"
        
        successful_calls = [s for s in stats if s['success']]
        
        if successful_calls:
            durations = [s['duration'] for s in successful_calls]
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)
        else:
            avg_duration = max_duration = min_duration = 0
        
        return {
            'total_calls': len(stats),
            'successful_calls': len(successful_calls),
            'success_rate': len(successful_calls) / len(stats) * 100,
            'avg_duration': avg_duration,
            'max_duration': max_duration,
            'min_duration': min_duration,
            'error_breakdown': dict(self.error_stats)
        }
```

## 배포 및 운영

### Docker를 이용한 배포

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 환경 변수 설정
ENV PYTHONPATH=/app
ENV HOST=0.0.0.0
ENV PORT=8000

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# 실행
CMD ["python", "-m", "mcp_kr_realestate"]
```

### 프로덕션 체크리스트

- [ ] 모든 필수 API 키 설정 완료
- [ ] 로그 레벨 INFO로 설정
- [ ] 에러 알림 설정 (Slack, 이메일 등)
- [ ] 데이터 백업 정책 수립
- [ ] 모니터링 대시보드 구성
- [ ] API 사용량 모니터링 설정
- [ ] 보안 검토 완료 (API 키 노출 방지)
- [ ] 성능 테스트 완료
- [ ] 장애 대응 시나리오 테스트
- [ ] 데이터 정리 스케줄 설정

## 문제 해결

### 일반적인 문제

#### 1. 국토교통부 실거래가 API 오류
**문제**: `SERVICE_KEY_IS_NOT_REGISTERED_ERROR`
```python
# 해결 방법: 서비스키 재확인 및 URL 인코딩
import urllib.parse

service_key = "YOUR_SERVICE_KEY"
encoded_key = urllib.parse.quote(service_key, safe='')

url = f"http://openapi.molit.go.kr:8081/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/getRTMSDataSvcAptTrade?serviceKey={encoded_key}&LAWD_CD=11680&DEAL_YMD=202406"
```

#### 2. 건축HUB API 전환 문제 (⚠️ 2025년 신규)
**문제**: 기존 건축물대장 API 호출 실패
```python
# 해결 방법: 새로운 건축HUB API 사용
# 기존 API (사용 중단)
old_url = "https://apis.data.go.kr/1613000/BldRgstService_v2/getBrTitleInfo"

# 신규 API (2025년 사용)
new_url = "https://www.hub.go.kr/portal/psg/openapi/getBldgTitle"

def get_building_info_new(api_key, sigungu_cd, bjdong_cd, bun, ji):
    """새로운 건축HUB API 사용"""
    params = {
        'serviceKey': api_key,
        'sigunguCd': sigungu_cd,
        'bjdongCd': bjdong_cd,
        'bun': bun,
        'ji': ji,
        '_type': 'json'  # JSON 형식 요청
    }
    response = requests.get(new_url, params=params)
    return response.json()
```

#### 3. 소상공인진흥공단 API 데이터 구조 변경 (⚠️ 2025년 변경)
**문제**: 기존 상가업소번호로 연계 불가
```python
# 해결 방법: 새로운 데이터 구조 적용
def handle_shop_data_change():
    """2025년 상권정보 데이터 구조 변경 대응"""
    
    # 새로운 업종분류 체계
    new_classification = {
        "대분류": 10,    # 기존과 동일
        "중분류": 75,    # 기존과 유사  
        "소분류": 247    # 837개 → 247개로 대폭 축소
    }
    
    # 주의사항
    print("⚠️ 2025년 변경사항:")
    print("1. 상가업소번호 체계 변경 - 과거 데이터와 연계 불가")
    print("2. 표준산업분류 9차 → 10차 변경")
    print("3. 상권업종분류 837개 → 247개로 개편")
    
    return new_classification
```

#### 4. 한국은행 ECOS API 오류
**문제**: `ECOS_UNAUTHORIZED`
```python
# 해결 방법: API 키 형식 검증
def validate_ecos_key(api_key):
    # ECOS API 키는 40자리 영숫자
    if len(api_key) != 40:
        raise ValueError("ECOS API 키는 40자리여야 합니다")
    
    # 테스트 호출
    test_url = f"https://ecos.bok.or.kr/api/KeyStatisticList/{api_key}/json/kr/1/10"
    response = requests.get(test_url)
    
    if response.status_code != 200:
        raise ValueError("API 키가 유효하지 않습니다")
    
    return True
```

### 2025년 디버깅 및 문제 해결

#### API 상태 확인
```python
def check_api_status():
    """주요 API 서비스 상태 확인"""
    
    apis_to_check = {
        "공공데이터포털": "https://www.data.go.kr",
        "한국부동산원": "https://www.reb.or.kr",
        "한국은행 ECOS": "https://ecos.bok.or.kr",
        "서울 열린데이터": "https://data.seoul.go.kr"
    }
    
    for name, url in apis_to_check.items():
        try:
            response = requests.get(url, timeout=5)
            status = "✅ 정상" if response.status_code == 200 else "❌ 문제"
            print(f"{name}: {status}")
        except:
            print(f"{name}: ❌ 연결 실패")
```

## 성능 최적화

- **병렬 처리**: 다중 API 호출 시 비동기 처리로 성능 향상
- **캐싱**: 자주 사용되는 데이터의 로컬 캐시 활용
- **배치 처리**: 대량 데이터 처리 시 배치 방식 적용
- **API 로드 밸런싱**: 여러 API 키 순환 사용으로 제한 회피
- **데이터 압축**: 대용량 데이터 전송 시 압축 활용
- **연결 풀링**: HTTP 연결 재사용으로 오버헤드 감소

## 보안 고려사항

- **API 키 관리**: 환경 변수로 관리하여 코드에 직접 노출 방지
- **데이터 암호화**: 민감한 투자 정보의 로컬 저장 시 암호화 적용
- **접근 제어**: API 호출량 제한을 통한 과도한 사용 방지
- **로그 관리**: 민감 정보 로그 기록 방지 및 로그 보안 강화
- **정기 갱신**: API 키 및 인증서 정기 갱신
- **취약점 점검**: 정기적인 보안 취약점 점검 및 업데이트

## 2025년 개발 계획

### 진행 중
- ✅ 건축HUB API 완전 통합
- ✅ 소상공인진흥공단 신규 데이터 구조 적용
- 🔄 추가 지역 API 통합 검토
- 🔄 AI 기반 분석 기능 강화

### 향후 계획
- 📱 모바일 앱 개발
- 🎨 사용자 인터페이스 개선
- 📚 문서화 및 가이드 확충
- 🌐 다국어 지원 (영어, 중국어)
- 🔗 외부 서비스 연동 (증권사, 은행 등)

## 라이선스

이 프로젝트는 [MIT 라이선스](LICENSE)를 따릅니다.

## 기여하기

기여를 환영합니다! 다음 절차를 따라주세요:

1. 저장소를 포크합니다
2. 기능 브랜치를 생성합니다 (`git checkout -b feature/new-analysis`)
3. 변경사항을 커밋합니다 (`git commit -am 'Add new analysis feature'`)
4. 브랜치에 푸시합니다 (`git push origin feature/new-analysis`)
5. Pull Request를 제출합니다

### 기여 가이드라인

- 코드 품질을 위해 `black`, `flake8`, `mypy` 사용
- 테스트 커버리지 80% 이상 유지
- 문서화 업데이트 필수
- 이슈 템플릿 활용

## 지원 및 문의

- **이슈 리포트**: [GitHub Issues](https://github.com/ChangooLee/mcp-kr-realestate/issues)
- **기능 요청**: [GitHub Discussions](https://github.com/ChangooLee/mcp-kr-realestate/discussions)
- **문서**: [Wiki](https://github.com/ChangooLee/mcp-kr-realestate/wiki)
- **2025년 변경사항**: [Change Log](https://github.com/ChangooLee/mcp-kr-realestate/blob/main/CHANGELOG.md)
- **개발자 연락처**: lchangoo@gmail.com
- **커뮤니티**: [Discord](https://discord.gg/mcp-kr-realestate)

## 업데이트 히스토리

### v2.2.0 (2025-06-13) - 현재 버전
- 🆕 장애 대응 시스템 추가
- 🆕 성능 모니터링 대시보드
- 🆕 데이터 관리 정책 강화
- 🆕 Docker 지원 및 프로덕션 가이드
- 🆕 초보자용 5분 퀘스트 추가
- ✅ API 응답 예시 및 상세 설명 보완

### v2.1.0 (2025-06-13)
- ✅ 건축HUB API 완전 통합
- ✅ 소상공인진흥공단 2025년 데이터 구조 변경 적용
- ✅ 모든 API URL 검증 완료
- ✅ 법정동코드 업데이트
- ✅ 새로운 디버깅 도구 추가

### v2.0.0 (2025-03-01)
- 🔄 MCP 2.0 프로토콜 적용
- 🔄 Claude Desktop 통합 개선
- 🔄 API 호출 최적화

### v1.5.0 (2024-12-01)
- 📊 포트폴리오 분석 기능 강화
- 📊 리스크 분석 도구 추가
- 📊 보고서 생성 자동화

---

**프로젝트 관리자**: 이찬구 (Changoo Lee)  
**연락처**: lchangoo@gmail.com  
**GitHub**: https://github.com/ChangooLee/mcp-kr-realestate  
**블로그**: https://changoo.tech  
**LinkedIn**: https://linkedin.com/in/changoo-lee  

**참고**: 이 프로젝트는 공공 API를 활용한 분석 도구로, 투자 결정에 대한 최종 책임은 사용자에게 있습니다. 실제 투자 시에는 전문가와 상담하시기 바랍니다.

**⚠️ 2025년 주요 변경사항**: 일부 API 서비스의 구조 변경으로 인해 기존 코드 수정이 필요할 수 있습니다. 자세한 내용은 [Change Log](https://github.com/ChangooLee/mcp-kr-realestate/blob/main/CHANGELOG.md)를 참조하세요.

**🎯 향후 로드맵**: 
- 2025년 Q3: AI 분석 고도화 및 실시간 알림 시스템
- 2025년 Q4: 모바일 앱 출시 및 다국어 지원
- 2026년 Q1: 글로벌 부동산 데이터 통합