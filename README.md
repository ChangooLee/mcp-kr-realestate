[한국어] | [English](README_en.md)

# MCP 부동산 투자 분석 서버

![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)

> **⚠️ 본 프로젝트는 비상업적(Non-Commercial) 용도로만 사용 가능합니다.**
> 
> This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0). Commercial use is strictly prohibited.

![License](https://img.shields.io/github/license/ChangooLee/mcp-kr-realestate)
![GitHub Stars](https://img.shields.io/github/stars/ChangooLee/mcp-kr-realestate)
![GitHub Issues](https://img.shields.io/github/issues/ChangooLee/mcp-kr-realestate)
![GitHub Last Commit](https://img.shields.io/github/last-commit/ChangooLee/mcp-kr-realestate)

한국 부동산 투자 분석을 위한 Model Context Protocol(MCP) 서버입니다. 다양한 공공 API를 통합하여 포괄적인 부동산 투자 분석과 자동화된 보고서 생성을 지원합니다.

**🔗 GitHub Repository**: https://github.com/ChangooLee/mcp-kr-realestate

---

## 주요 특징

- **🏢 포괄적 자산군 분석** - 아파트, 오피스텔, 단독/다가구, 연립다세대, 상업업무용, 산업용(공장/창고), 토지 등 7개 자산군의 매매/전월세 실거래가 데이터 지원
- **📊 실시간 데이터 연동** - 국토교통부 공공데이터포털, 한국은행 ECOS API 등 다중 공공 API 통합
- **🌍 전국 단위 분석** - 법정동 단위 지역별 실거래가 분석, 100대 거시지표 통합검색 지원
- **🤖 AI 친화적 설계** - MCP(Model Context Protocol) 기반으로 Claude, GPT 등 AI 모델과 직접 연동 가능
- **📈 고급 통계 분석** - 자산별 가격 통계, 평당가 분석, 건물 특성별/입지별 세분화 분석
- **🛡️ 스마트 캐싱 시스템** - 자동 데이터 캐싱, 중복 요청 방지, API 장애 시 캐시 데이터 활용

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
PUBLIC_DATA_API_KEY_ENCODED=발급받은_공공데이터_API키(URL인코딩된_형태)
ECOS_API_KEY=발급받은_ECOS_API키
HOST=0.0.0.0
PORT=8001
TRANSPORT=stdio
LOG_LEVEL=INFO
MCP_SERVER_NAME=kr-realestate-mcp
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

### 2. ECOS 경제지표 검색 및 활용

```python
from mcp_kr_realestate.tools.analysis_tools import search_realestate_indicators, get_ecos_key_statistic_list

# 1. 부동산 관련 주요 경제지표 검색
search_result = search_realestate_indicators({"keyword": "주택매매가격지수"})
print(search_result.text)  # 관련 지표의 최신값, 단위, 기준일 등

# 2. ECOS 100대 주요지표 목록 조회
key_stats = get_ecos_key_statistic_list({"start": 1, "end": 100})
print(key_stats.text)  # 캐시 파일 경로와 주요 지표 미리보기

# 3. 특정 통계 데이터 조회 (예: 기준금리)
from mcp_kr_realestate.tools.analysis_tools import get_ecos_statistic_search
ecos_data = get_ecos_statistic_search({
    "stat_code": "722Y001", 
    "cycle": "M", 
    "start_time": "202401", 
    "end_time": "202412"
})
print(ecos_data.text)  # 캐시된 데이터 파일 경로
```

### 3. 캐시/자동갱신/파일경로 활용

- 모든 데이터는 `/src/mcp_kr_realestate/utils/cache/`에 자동 저장/갱신됨
- 분석 도구는 캐시 파일 경로만 반환 → pandas 등으로 직접 로드 가능

---

## 🧰 주요 도구별 사용법

### 📋 실거래가 데이터 수집 도구 (13개)

| 도구명 | 설명 | 주요 파라미터 | 반환값 |
|--------|------|---------------|--------|
| **get_region_codes** | 지역명으로 법정동코드 조회 | region_name | 코드 목록(미리보기 5건) |
| **get_apt_trade_data** | 아파트 매매 실거래가 수집 | region_code, year_month | JSON 파일 경로 |
| **get_apt_rent_data** | 아파트 전월세 실거래가 수집 | region_code, year_month | JSON 파일 경로 |
| **get_officetel_trade_data** | 오피스텔 매매 실거래가 수집 | region_code, year_month | JSON 파일 경로 |
| **get_officetel_rent_data** | 오피스텔 전월세 실거래가 수집 | region_code, year_month | JSON 파일 경로 |
| **get_single_detached_house_trade_data** | 단독/다가구 매매 실거래가 수집 | region_code, year_month | JSON 파일 경로 |
| **get_single_detached_house_rent_data** | 단독/다가구 전월세 실거래가 수집 | region_code, year_month | JSON 파일 경로 |
| **get_row_house_trade_data** | 연립다세대 매매 실거래가 수집 | region_code, year_month | JSON 파일 경로 |
| **get_row_house_rent_data** | 연립다세대 전월세 실거래가 수집 | region_code, year_month | JSON 파일 경로 |
| **get_commercial_property_trade_data** | 상업업무용 매매 실거래가 수집 | region_code, year_month | JSON 파일 경로 |
| **get_industrial_property_trade_data** | 산업용(공장/창고) 매매 실거래가 수집 | region_code, year_month | JSON 파일 경로 |
| **get_land_trade_data** | 토지 매매 실거래가 수집 | region_code, year_month | JSON 파일 경로 |
| **get_transaction_cache_data** | 캐시된 거래 데이터 검색/필터링 | asset_type, region_code, year_months, field_name, field_value_substring | 미리보기 + 통계 요약 |

### 📊 실거래가 분석 도구 (11개)

| 도구명 | 설명 | 주요 파라미터 | 반환값 |
|--------|------|---------------|--------|
| **analyze_apartment_trade** | 아파트 매매 데이터 분석 | file_path | 통계 요약 JSON (단지별/동별/가격 통계) |
| **analyze_apartment_rent** | 아파트 전월세 데이터 분석 | file_path | 통계 요약 JSON (전세/월세 구분) |
| **analyze_officetel_trade** | 오피스텔 매매 데이터 분석 | file_path | 통계 요약 JSON (단지별/동별/가격 통계) |
| **analyze_officetel_rent** | 오피스텔 전월세 데이터 분석 | file_path | 통계 요약 JSON (전세/월세 구분) |
| **analyze_single_detached_house_trade** | 단독/다가구 매매 데이터 분석 | file_path | 통계 요약 JSON (건물별/동별/연면적 기준) |
| **analyze_single_detached_house_rent** | 단독/다가구 전월세 데이터 분석 | file_path | 통계 요약 JSON (전세/월세 구분) |
| **analyze_row_house_trade** | 연립다세대 매매 데이터 분석 | file_path | 통계 요약 JSON (단지별/동별/전용면적 기준) |
| **analyze_row_house_rent** | 연립다세대 전월세 데이터 분석 | file_path | 통계 요약 JSON (전세/월세 구분) |
| **analyze_commercial_property_trade** | 상업업무용 매매 데이터 분석 | file_path | 통계 요약 JSON (용도별/입지별/건물 특성별) |
| **analyze_industrial_property_trade** | 산업용(공장/창고) 매매 데이터 분석 | file_path | 통계 요약 JSON (용도별/동별/건물 특성별) |
| **analyze_land_trade** | 토지 매매 데이터 분석 | file_path | 통계 요약 JSON (지목별/동별/토지면적 기준) |

### 🏦 ECOS/거시지표 도구 (6개)

| 도구명 | 설명 | 주요 파라미터 | 반환값 |
|--------|------|---------------|--------|
| **get_ecos_statistic_table_list** | ECOS 통계표 목록 조회 및 캐싱 | start, end, stat_code | 캐시 파일 경로 |
| **get_ecos_statistic_word** | ECOS 통계용어사전 조회 및 캐싱 | word, start, end | 캐시 파일 경로 |
| **get_ecos_statistic_item_list** | ECOS 통계 세부항목 목록 조회 및 캐싱 | stat_code, start, end | 캐시 파일 경로 |
| **get_ecos_statistic_search** | ECOS 통계 데이터 조회 및 캐싱 | stat_code, cycle, start_time, end_time, item_code1~4 | 캐시 파일 경로 |
| **get_ecos_key_statistic_list** | ECOS 100대 주요지표 조회 및 캐싱 | start, end | 캐시 파일 경로 + pandas 미리보기 |
| **search_realestate_indicators** | 100대 주요지표에서 부동산/금리/거시지표 키워드 검색 | keyword | 관련 지표의 최신값, 단위, 기준일 |

> **📌 상관분석 도구**: 부동산-거시지표 상관/회귀분석 도구는 현재 개발 중입니다.

> **자세한 파라미터/반환값/예시는 각 도구의 docstring 및 `src/mcp_kr_realestate/tools/analysis_tools.py` 참고**

---

## 🖥️ MCP 클라이언트 연동 가이드

### Claude Desktop 연동
```json
{
  "mcpServers": {
    "kr-realestate": {
      "command": "/your/path/.venv/bin/mcp-kr-realestate",
      "env": {
        "PUBLIC_DATA_API_KEY_ENCODED": "your_api_key_here",
        "ECOS_API_KEY": "your_ecos_key_here"
      }
    }
  }
}
```

### 지원 플랫폼
- **macOS**: Intel/Apple Silicon 모두 지원
- **Windows**: Windows 10/11 지원
- **Linux**: Ubuntu 20.04+ 지원

### 필수 의존성
- Python 3.10+
- requests, pandas, python-dotenv
- fastmcp 2.2.3, mcp 1.6.0

---

## ⚠️ 중요 참고사항

### API 키 설정
1. **공공데이터포털 API 키**: [data.go.kr](https://data.go.kr)에서 발급 (URL 인코딩 필요)
2. **ECOS API 키**: [한국은행 ECOS](https://ecos.bok.or.kr)에서 발급

### 데이터 관리
- 모든 데이터는 `src/mcp_kr_realestate/utils/cache/`에 자동 캐싱
- 캐시 파일은 24시간 주기로 자동 갱신됨
- 수동 캐시 삭제/갱신 가능

### 알려진 제한사항
- **지역별 데이터**: 거래가 없는 지역/기간의 경우 빈 결과 반환
- **API 응답속도**: 대용량 데이터 조회 시 1-3초 소요 가능
- **개발 예정 기능**: 부동산-거시지표 상관분석, 포트폴리오 최적화, AI 보고서 생성

---

## 📝 기여/문의/라이선스

- 기여 방법, 이슈/문의, 라이선스(기존 내용 유지)

### 라이선스

이 프로젝트는 [CC BY-NC 4.0 (비상업적 이용만 허용)](https://creativecommons.org/licenses/by-nc/4.0/) 라이선스를 따릅니다.

- **비상업적, 개인, 연구/학습, 비영리 목적에 한해 사용 가능합니다.**
- **영리기업, 상업적 서비스, 수익 창출 목적의 사용은 엄격히 금지됩니다.**
- 사용 목적이 불분명할 경우 반드시 저작자(Changoo Lee)에게 문의하시기 바랍니다.
- 자세한 내용은 LICENSE 파일과 위 링크를 참고하세요.

> **English:**
> This project is licensed under CC BY-NC 4.0. Use is permitted only for non-commercial, personal, academic/research, or non-profit purposes. Any use by for-profit companies, commercial services, or in any revenue-generating activity is strictly prohibited. See the LICENSE file for details.

---

**프로젝트 관리자**: 이찬구 (Changoo Lee)  
**연락처**: lchangoo@gmail.com  
**GitHub**: https://github.com/ChangooLee/mcp-kr-realestate  
**블로그**: https://changoo.tech  
**LinkedIn**: https://linkedin.com/in/changoo-lee  

**참고**: 이 프로젝트는 공공 API를 활용한 분석 도구로, 투자 결정에 대한 최종 책임은 사용자에게 있습니다. 실제 투자 시에는 전문가와 상담하시기 바랍니다.

**⚠️ 2025년 주요 변경사항**: 일부 API 서비스의 구조 변경으로 인해 기존 코드 수정이 필요할 수 있습니다. 자세한 내용은 [Change Log](https://github.com/ChangooLee/mcp-kr-realestate/blob/main/CHANGELOG.md)를 참조하세요.