# MCP 부동산 투자 분석 서버

![License](https://img.shields.io/github/license/ChangooLee/mcp-kr-realestate)
![GitHub Stars](https://img.shields.io/github/stars/ChangooLee/mcp-kr-realestate)
![GitHub Issues](https://img.shields.io/github/issues/ChangooLee/mcp-kr-realestate)
![GitHub Last Commit](https://img.shields.io/github/last-commit/ChangooLee/mcp-kr-realestate)

한국 부동산 투자 분석을 위한 Model Context Protocol(MCP) 서버입니다. 다양한 공공 API를 통합하여 포괄적인 부동산 투자 분석과 자동화된 보고서 생성을 지원합니다.

**🔗 GitHub Repository**: https://github.com/ChangooLee/mcp-kr-realestate

---

## 주요 특징

- **🏢 다양한 자산군 분석** - 아파트, 오피스텔, 단독/다가구, 연립다세대, 상업업무용, 토지 등 실거래가 데이터 지원
- **📊 실시간 데이터 연동** - 국토교통부, 한국은행 ECOS 등 공공 API 통합
- **🌍 전국 단위 분석** - 지역별 실거래가, 거시지표, 상관분석 등 전국 단위 지원
- **🤖 AI 보고서 생성** - (개발 예정) 맞춤형 투자 분석 보고서 자동 생성
- **📈 고급 분석** - 실거래가 통계, ECOS 통합검색, 부동산-거시지표 상관/회귀분석 등
- **🛡️ 장애 대응 시스템** - API 장애 시 자동 캐시/대체 데이터 활용

---

## 🔰 빠른 시작 (Quick Start)

### 1. Python 3.10+ 설치

#### macOS
```sh
brew install python@3.10
```
#### Windows
- [python.org](https://www.python.org/downloads/windows/)에서 설치, "Add Python to PATH" 체크
#### Linux (Ubuntu)
```sh
sudo apt update
sudo apt install python3.10 python3.10-venv python3.10-distutils
```

### 2. 프로젝트 설치

```sh
git clone https://github.com/ChangooLee/mcp-kr-realestate.git
cd mcp-kr-realestate
python3.10 -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install --upgrade pip
pip install -e .
```

### 3. 환경 변수 설정

`.env` 파일 예시:
```env
PUBLIC_DATA_API_KEY=발급받은_공공데이터_API키
ECOS_API_KEY=발급받은_ECOS_API키
SEOUL_DATA_API_KEY=서울_API키
KOSIS_API_KEY=KOSIS_API키
HOST=0.0.0.0
PORT=8000
TRANSPORT=stdio
LOG_LEVEL=INFO
```

---

## 🛠️ 실제 사용 예시

### 1. 실거래가 데이터 수집 및 분석

```python
from mcp_kr_realestate.tools.transaction_tools import get_apt_trade_data
from mcp_kr_realestate.tools.analysis_tools import analyze_apartment_trade

# 1. 아파트 매매 실거래가 데이터 수집 (2025년 5월, 강남구)
result = get_apt_trade_data(region_code="11680", year_month="202505")
print(result.text)  # 저장된 JSON 파일 경로 반환

# 2. 데이터 분석 및 리포트 생성
summary = analyze_apartment_trade(file_path=result.text)
print(summary.text)  # 통계 요약 JSON 반환
```

### 2. ECOS 통합검색 및 상관분석

```python
from mcp_kr_realestate.tools.analysis_tools import search_realestate_indicators, analyze_correlation_with_realestate

# 1. 금리 관련 주요 경제지표 검색 및 미리보기
search_result = search_realestate_indicators({"keyword": "기준금리"})
print(search_result.text)  # 관련 통계표, 데이터 프리뷰, 추천 stat_code 등

# 2. 부동산 가격과 금리 상관분석 (2025년 기준)
params = {
    "realestate_type": "아파트",
    "region_code": "11680",
    "stat_code": "722Y001",  # (예: 기준금리)
    "cycle": "M",
    "start_time": "202401",
    "end_time": "202505"
}
corr_result = analyze_correlation_with_realestate(params)
print(corr_result.text)  # 상관계수, 회귀분석, 데이터 정렬 결과 등
```

### 3. 캐시/자동갱신/파일경로 활용

- 모든 데이터는 `/src/mcp_kr_realestate/utils/cache/`에 자동 저장/갱신됨
- 분석 도구는 캐시 파일 경로만 반환 → pandas 등으로 직접 로드 가능

---

## 🧰 주요 도구별 사용법

### 실거래가 데이터 수집 도구

| 도구명 | 설명 | 주요 파라미터 | 반환값 |
|--------|------|---------------|--------|
| get_region_codes | 지역명으로 법정동코드 조회 | region_name | 코드 목록(preview) |
| get_apt_trade_data | 아파트 매매 실거래가 수집 | region_code, year_month | JSON 파일 경로 |
| get_apt_rent_data | 아파트 전월세 실거래가 수집 | region_code, year_month | JSON 파일 경로 |
| get_officetel_trade_data | 오피스텔 매매 실거래가 수집 | region_code, year_month | JSON 파일 경로 |
| get_officetel_rent_data | 오피스텔 전월세 실거래가 수집 | region_code, year_month | JSON 파일 경로 |
| get_single_detached_house_trade_data | 단독/다가구 매매 실거래가 수집 | region_code, year_month | JSON 파일 경로 |
| get_single_detached_house_rent_data | 단독/다가구 전월세 실거래가 수집 | region_code, year_month | JSON 파일 경로 |
| get_row_house_trade_data | 연립다세대 매매 실거래가 수집 | region_code, year_month | JSON 파일 경로 |
| get_row_house_rent_data | 연립다세대 전월세 실거래가 수집 | region_code, year_month | JSON 파일 경로 |
| get_commercial_property_trade_data | 상업업무용 매매 실거래가 수집 | region_code, year_month | JSON 파일 경로 |
| get_industrial_property_trade_data | 산업용(공장/창고) 매매 실거래가 수집 | region_code, year_month | JSON 파일 경로 |
| get_land_trade_data | 토지 매매 실거래가 수집 | region_code, year_month | JSON 파일 경로 |

### 실거래가 분석 도구

| 도구명 | 설명 | 주요 파라미터 | 반환값 |
|--------|------|---------------|--------|
| analyze_apartment_trade | 아파트 매매 데이터 분석 | file_path | 통계 요약 JSON |
| analyze_apartment_rent | 아파트 전월세 데이터 분석 | file_path | 통계 요약 JSON |
| analyze_officetel_trade | 오피스텔 매매 데이터 분석 | file_path | 통계 요약 JSON |
| analyze_officetel_rent | 오피스텔 전월세 데이터 분석 | file_path | 통계 요약 JSON |
| analyze_single_detached_house_trade | 단독/다가구 매매 데이터 분석 | file_path | 통계 요약 JSON |
| analyze_single_detached_house_rent | 단독/다가구 전월세 데이터 분석 | file_path | 통계 요약 JSON |
| analyze_row_house_trade | 연립다세대 매매 데이터 분석 | file_path | 통계 요약 JSON |
| analyze_row_house_rent | 연립다세대 전월세 데이터 분석 | file_path | 통계 요약 JSON |
| analyze_commercial_property_trade | 상업업무용 매매 데이터 분석 | file_path | 통계 요약 JSON |
| analyze_industrial_property_trade | 산업용(공장/창고) 매매 데이터 분석 | file_path | 통계 요약 JSON |
| analyze_land_trade | 토지 매매 데이터 분석 | file_path | 통계 요약 JSON |

### ECOS/거시지표 도구

| 도구명 | 설명 | 주요 파라미터 | 반환값 |
|--------|------|---------------|--------|
| get_ecos_statistic_table_list | ECOS 통계표 목록 캐싱 | start, end, stat_code | 캐시 파일 경로 |
| get_ecos_statistic_word | ECOS 통계용어사전 캐싱 | word, start, end | 캐시 파일 경로 |
| get_ecos_statistic_item_list | ECOS 통계 세부항목 목록 캐싱 | stat_code, start, end | 캐시 파일 경로 |
| get_ecos_statistic_search | ECOS 통계 데이터 조회/캐싱 | stat_code, cycle, start_time, end_time, item_code1~4 | 캐시 파일 경로 |
| get_ecos_key_statistic_list | ECOS 100대 주요지표 캐싱 | start, end | 캐시 파일 경로 + pandas preview |
| search_realestate_indicators | 부동산/금리/가계 등 주요 경제지표 통합검색 | keyword | 관련 통계표, 데이터 프리뷰 |
| analyze_correlation_with_realestate | 부동산-거시지표 상관/회귀분석 | realestate_type, region_code, stat_code, cycle, start_time, end_time | 상관계수, 회귀분석 결과 |

> **자세한 파라미터/반환값/예시는 각 도구의 docstring 및 `src/mcp_kr_realestate/tools/analysis_tools.py` 참고**

---

## 🖥️ 멀티플랫폼/IDE/AI 연동

- macOS, Windows, Linux 모두 지원
- Claude Desktop 등 AI IDE 연동:  
  - `"command": "/your/path/.venv/bin/mcp-kr-realestate"`  
  - 환경변수는 `.env` 또는 config에서 지정

---

## ⚠️ 주의/FAQ

- API 키는 반드시 발급 후 `.env`에 저장
- 캐시 파일은 자동 관리, 직접 삭제/갱신 가능
- 데이터가 없거나 분석 실패시 상세 에러 메시지 반환
- 미구현 기능(포트폴리오 최적화, 리스크 분석, 보고서 자동생성 등)은 "개발 예정"으로 표기

---

## 📝 기여/문의/라이선스

- 기여 방법, 이슈/문의, 라이선스(기존 내용 유지)

---

**프로젝트 관리자**: 이찬구 (Changoo Lee)  
**연락처**: lchangoo@gmail.com  
**GitHub**: https://github.com/ChangooLee/mcp-kr-realestate  
**블로그**: https://changoo.tech  
**LinkedIn**: https://linkedin.com/in/changoo-lee  

**참고**: 이 프로젝트는 공공 API를 활용한 분석 도구로, 투자 결정에 대한 최종 책임은 사용자에게 있습니다. 실제 투자 시에는 전문가와 상담하시기 바랍니다.

**⚠️ 2025년 주요 변경사항**: 일부 API 서비스의 구조 변경으로 인해 기존 코드 수정이 필요할 수 있습니다. 자세한 내용은 [Change Log](https://github.com/ChangooLee/mcp-kr-realestate/blob/main/CHANGELOG.md)를 참조하세요.