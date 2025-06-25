[한국어](README.md) | English

# MCP Real Estate Investment Analytics Server

![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)

> **⚠️ This project is licensed for non-commercial use only.**
> 
> Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0). Commercial use is strictly prohibited.

---

## Overview

MCP Real Estate is a Model Context Protocol (MCP) server for advanced real estate investment analytics in Korea. It integrates multiple public APIs (Ministry of Land, Bank of Korea ECOS, etc.) to provide comprehensive data collection, statistical analysis, and automated reporting for real estate assets.

---

## Key Features

- **🏢 Multi-asset support**: Apartments, officetels, single/multi-family, commercial, industrial, land, etc.
- **📊 Real-time data**: Integrated with MOLIT, ECOS, and other public APIs
- **🌍 Nationwide analytics**: Regional transaction data, macro indicators, correlation analysis
- **🤖 AI report generation**: (Planned) Automated investment analysis reports
- **📈 Advanced analytics**: Transaction statistics, ECOS search, real estate-macro correlation/regression
- **🛡️ Robust caching**: Automatic data caching and fallback for API outages

---

## 🚀 Quick Start

### 1. Install Python 3.10+

#### macOS
```sh
brew install python@3.10
```
#### Windows
- Download from [python.org](https://www.python.org/downloads/windows/), check "Add Python to PATH"
#### Linux (Ubuntu)
```sh
sudo apt update
sudo apt install python3.10 python3.10-venv python3.10-distutils
```

### 2. Project Setup

```sh
git clone https://github.com/ChangooLee/mcp-kr-realestate.git
cd mcp-kr-realestate
python3.10 -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install --upgrade pip
pip install -e .
```

### 3. Environment Variables

Example `.env` file:
```env
PUBLIC_DATA_API_KEY=your_public_data_api_key
ECOS_API_KEY=your_ecos_api_key
SEOUL_DATA_API_KEY=your_seoul_api_key
KOSIS_API_KEY=your_kosis_api_key
HOST=0.0.0.0
PORT=8000
TRANSPORT=stdio
LOG_LEVEL=INFO
```

---

## 🛠️ Usage Examples

### 1. Collect and Analyze Transaction Data

```python
from mcp_kr_realestate.tools.transaction_tools import get_apt_trade_data
from mcp_kr_realestate.tools.analysis_tools import analyze_apartment_trade

# 1. Collect apartment sales data (May 2025, Gangnam-gu)
result = get_apt_trade_data(region_code="11680", year_month="202505")
print(result.text)  # Returns path to saved JSON file

# 2. Analyze and generate report
summary = analyze_apartment_trade(file_path=result.text)
print(summary.text)  # Returns statistical summary as JSON
```

### 2. ECOS Integrated Search & Correlation Analysis

```python
from mcp_kr_realestate.tools.analysis_tools import search_realestate_indicators, analyze_correlation_with_realestate

# 1. Search for key economic indicators (e.g., interest rate)
search_result = search_realestate_indicators({"keyword": "Base Rate"})
print(search_result.text)  # Related tables, data preview, recommended stat_code

# 2. Correlation analysis between real estate price and interest rate (2025 example)
params = {
    "realestate_type": "apartment",
    "region_code": "11680",
    "stat_code": "722Y001",  # (e.g., base rate)
    "cycle": "M",
    "start_time": "202401",
    "end_time": "202505"
}
corr_result = analyze_correlation_with_realestate(params)
print(corr_result.text)  # Correlation, regression, aligned data, etc.
```

### 3. Caching & File Usage

- All data is automatically cached under `/src/mcp_kr_realestate/utils/cache/`
- Analysis tools return only file paths; load with pandas or any text editor

---

## 🧰 Main Tools

### Transaction Data Collection

| Tool | Description | Parameters | Returns |
|------|-------------|------------|---------|
| get_region_codes | Search legal district codes by region name | region_name | Code list (preview) |
| get_apt_trade_data | Collect apartment sales data | region_code, year_month | JSON file path |
| get_apt_rent_data | Collect apartment rent data | region_code, year_month | JSON file path |
| get_officetel_trade_data | Collect officetel sales data | region_code, year_month | JSON file path |
| get_officetel_rent_data | Collect officetel rent data | region_code, year_month | JSON file path |
| get_single_detached_house_trade_data | Collect single/multi-family sales data | region_code, year_month | JSON file path |
| get_single_detached_house_rent_data | Collect single/multi-family rent data | region_code, year_month | JSON file path |
| get_row_house_trade_data | Collect row house sales data | region_code, year_month | JSON file path |
| get_row_house_rent_data | Collect row house rent data | region_code, year_month | JSON file path |
| get_commercial_property_trade_data | Collect commercial property sales data | region_code, year_month | JSON file path |
| get_industrial_property_trade_data | Collect industrial (factory/warehouse) sales data | region_code, year_month | JSON file path |
| get_land_trade_data | Collect land sales data | region_code, year_month | JSON file path |

### Transaction Data Analysis

| Tool | Description | Parameters | Returns |
|------|-------------|------------|---------|
| analyze_apartment_trade | Analyze apartment sales data | file_path | Statistical summary JSON |
| analyze_apartment_rent | Analyze apartment rent data | file_path | Statistical summary JSON |
| analyze_officetel_trade | Analyze officetel sales data | file_path | Statistical summary JSON |
| analyze_officetel_rent | Analyze officetel rent data | file_path | Statistical summary JSON |
| analyze_single_detached_house_trade | Analyze single/multi-family sales data | file_path | Statistical summary JSON |
| analyze_single_detached_house_rent | Analyze single/multi-family rent data | file_path | Statistical summary JSON |
| analyze_row_house_trade | Analyze row house sales data | file_path | Statistical summary JSON |
| analyze_row_house_rent | Analyze row house rent data | file_path | Statistical summary JSON |
| analyze_commercial_property_trade | Analyze commercial property sales data | file_path | Statistical summary JSON |
| analyze_industrial_property_trade | Analyze industrial sales data | file_path | Statistical summary JSON |
| analyze_land_trade | Analyze land sales data | file_path | Statistical summary JSON |

### ECOS/Macro Indicator Tools

| Tool | Description | Parameters | Returns |
|------|-------------|------------|---------|
| get_ecos_statistic_table_list | Cache ECOS statistic table list | start, end, stat_code | Cache file path |
| get_ecos_statistic_word | Cache ECOS glossary | word, start, end | Cache file path |
| get_ecos_statistic_item_list | Cache ECOS item list | stat_code, start, end | Cache file path |
| get_ecos_statistic_search | Query/cache ECOS data | stat_code, cycle, start_time, end_time, item_code1~4 | Cache file path |
| get_ecos_key_statistic_list | Cache ECOS 100 key indicators | start, end | Cache file path + pandas preview |
| search_realestate_indicators | Integrated search for real estate/macro indicators | keyword | Related tables, data preview |
| analyze_correlation_with_realestate | Correlation/regression between real estate and macro | realestate_type, region_code, stat_code, cycle, start_time, end_time | Correlation, regression, aligned data |

> For detailed parameters, return values, and examples, see the docstrings in `src/mcp_kr_realestate/tools/analysis_tools.py`.

---

## 🖥️ Multi-platform & IDE/AI Integration

- Supports macOS, Windows, Linux
- For AI IDEs (e.g., Claude Desktop):
  - `"command": "/your/path/.venv/bin/mcp-kr-realestate"`
  - Set environment variables via `.env` or config

---

## ⚠️ Notes & FAQ

- API keys must be set in `.env` before use
- Cache files are managed automatically; you may delete/refresh as needed
- If data is missing or analysis fails, a detailed error message is returned
- Unimplemented features (portfolio optimization, risk analysis, auto-reporting, etc.) are marked as "Planned"

---

## 📝 Contributing / Contact / License

- See CONTRIBUTING.md or open an issue for questions

### License

This project is licensed under the [CC BY-NC 4.0 (Non-Commercial Use Only)](https://creativecommons.org/licenses/by-nc/4.0/) license.

- **Use is permitted only for non-commercial, personal, academic/research, or non-profit purposes.**
- **Any use by for-profit companies, commercial services, or in any revenue-generating activity is strictly prohibited.**
- If you are unsure whether your use is permitted, please contact the author (Changoo Lee).
- See the LICENSE file and the link above for full details.

> **한국어:**
> 본 프로젝트는 CC BY-NC 4.0 라이선스 하에 배포되며, 비상업적, 개인, 연구/학습, 비영리 목적에 한해 사용 가능합니다. 영리기업, 상업적 서비스, 수익 창출 목적의 사용은 엄격히 금지됩니다. 자세한 내용은 LICENSE 파일을 참고하세요.

---

> 한국어 안내는 [README.md](README.md)에서 확인하세요. 