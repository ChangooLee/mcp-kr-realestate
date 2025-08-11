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

- **🏢 Comprehensive Multi-Asset Coverage**: Complete support for 7 asset classes - apartments, officetels, single/multi-family homes, row houses, commercial properties, industrial facilities (factories/warehouses), and land with both sales and rental transaction data
- **📊 Real-time Data Integration**: Seamless integration with Korea Ministry of Land's Public Data Portal and Bank of Korea ECOS APIs for live market data
- **🌍 Nationwide Geographic Coverage**: Legal dong-level regional analysis with support for Bank of Korea's top 100 macroeconomic indicators
- **🤖 AI-Native Architecture**: Built on Model Context Protocol (MCP) for direct integration with Claude, GPT, and other AI models
- **📈 Advanced Statistical Analytics**: Asset-specific price statistics, price-per-pyeong analysis, segmented analysis by building characteristics and location
- **🛡️ Smart Caching System**: Automated data caching, duplicate request prevention, and cache fallback during API outages

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
PUBLIC_DATA_API_KEY_ENCODED=your_public_data_api_key_url_encoded
ECOS_API_KEY=your_ecos_api_key
HOST=0.0.0.0
PORT=8001
TRANSPORT=stdio
LOG_LEVEL=INFO
MCP_SERVER_NAME=kr-realestate-mcp
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

### 2. ECOS Economic Indicators Search & Utilization

```python
from mcp_kr_realestate.tools.analysis_tools import search_realestate_indicators, get_ecos_key_statistic_list

# 1. Search for real estate related economic indicators
search_result = search_realestate_indicators({"keyword": "Housing Price Index"})
print(search_result.text)  # Latest values, units, reference dates

# 2. Retrieve ECOS top 100 key indicators list
key_stats = get_ecos_key_statistic_list({"start": 1, "end": 100})
print(key_stats.text)  # Cache file path and key indicators preview

# 3. Query specific statistical data (e.g., base rate)
from mcp_kr_realestate.tools.analysis_tools import get_ecos_statistic_search
ecos_data = get_ecos_statistic_search({
    "stat_code": "722Y001", 
    "cycle": "M", 
    "start_time": "202401", 
    "end_time": "202412"
})
print(ecos_data.text)  # Cached data file path
```

### 3. Caching, Auto-refresh & File Path Utilization

- All data is automatically saved/refreshed in `/src/mcp_kr_realestate/utils/cache/`
- Analysis tools return only cache file paths → can be directly loaded with pandas or other tools

---

## 🧰 Main Tools Overview

### 📋 Transaction Data Collection Tools (13 tools)

| Tool | Description | Parameters | Returns |
|------|-------------|------------|---------|
| **get_region_codes** | Search legal district codes by region name | region_name | Code list (preview 5 items) |
| **get_apt_trade_data** | Collect apartment sales data | region_code, year_month | JSON file path |
| **get_apt_rent_data** | Collect apartment rent data | region_code, year_month | JSON file path |
| **get_officetel_trade_data** | Collect officetel sales data | region_code, year_month | JSON file path |
| **get_officetel_rent_data** | Collect officetel rent data | region_code, year_month | JSON file path |
| **get_single_detached_house_trade_data** | Collect single/multi-family sales data | region_code, year_month | JSON file path |
| **get_single_detached_house_rent_data** | Collect single/multi-family rent data | region_code, year_month | JSON file path |
| **get_row_house_trade_data** | Collect row house sales data | region_code, year_month | JSON file path |
| **get_row_house_rent_data** | Collect row house rent data | region_code, year_month | JSON file path |
| **get_commercial_property_trade_data** | Collect commercial property sales data | region_code, year_month | JSON file path |
| **get_industrial_property_trade_data** | Collect industrial (factory/warehouse) sales data | region_code, year_month | JSON file path |
| **get_land_trade_data** | Collect land sales data | region_code, year_month | JSON file path |
| **get_transaction_cache_data** | Search/filter cached transaction data | asset_type, region_code, year_months, field_name, field_value_substring | Preview + statistics summary |

### 📊 Transaction Data Analysis Tools (11 tools)

| Tool | Description | Parameters | Returns |
|------|-------------|------------|---------|
| **analyze_apartment_trade** | Analyze apartment sales data | file_path | Statistical summary JSON (by complex/dong/price stats) |
| **analyze_apartment_rent** | Analyze apartment rent data | file_path | Statistical summary JSON (jeonse/wolse separated) |
| **analyze_officetel_trade** | Analyze officetel sales data | file_path | Statistical summary JSON (by complex/dong/price stats) |
| **analyze_officetel_rent** | Analyze officetel rent data | file_path | Statistical summary JSON (jeonse/wolse separated) |
| **analyze_single_detached_house_trade** | Analyze single/multi-family sales data | file_path | Statistical summary JSON (by building/dong/gross floor area) |
| **analyze_single_detached_house_rent** | Analyze single/multi-family rent data | file_path | Statistical summary JSON (jeonse/wolse separated) |
| **analyze_row_house_trade** | Analyze row house sales data | file_path | Statistical summary JSON (by complex/dong/exclusive area) |
| **analyze_row_house_rent** | Analyze row house rent data | file_path | Statistical summary JSON (jeonse/wolse separated) |
| **analyze_commercial_property_trade** | Analyze commercial property sales data | file_path | Statistical summary JSON (by use type/location/building features) |
| **analyze_industrial_property_trade** | Analyze industrial sales data | file_path | Statistical summary JSON (by use type/dong/building features) |
| **analyze_land_trade** | Analyze land sales data | file_path | Statistical summary JSON (by land type/dong/land area) |

### 🏦 ECOS/Macro Indicator Tools (6 tools)

| Tool | Description | Parameters | Returns |
|------|-------------|------------|---------|
| **get_ecos_statistic_table_list** | Query and cache ECOS statistic table list | start, end, stat_code | Cache file path |
| **get_ecos_statistic_word** | Query and cache ECOS statistical glossary | word, start, end | Cache file path |
| **get_ecos_statistic_item_list** | Query and cache ECOS statistic item list | stat_code, start, end | Cache file path |
| **get_ecos_statistic_search** | Query and cache ECOS statistical data | stat_code, cycle, start_time, end_time, item_code1~4 | Cache file path |
| **get_ecos_key_statistic_list** | Query and cache ECOS 100 key indicators | start, end | Cache file path + pandas preview |
| **search_realestate_indicators** | Keyword search in 100 key indicators for real estate/interest rate/macro indicators | keyword | Latest values, units, reference dates |

> **📌 Correlation Analysis Tool**: Real estate-macro correlation/regression analysis tool is currently under development.

> For detailed parameters, return values, and examples, see the docstrings in `src/mcp_kr_realestate/tools/analysis_tools.py`.

---

## 🖥️ MCP Client Integration Guide

### Claude Desktop Integration
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

### Supported Platforms
- **macOS**: Both Intel and Apple Silicon supported
- **Windows**: Windows 10/11 supported
- **Linux**: Ubuntu 20.04+ supported

### Required Dependencies
- Python 3.10+
- requests, pandas, python-dotenv
- fastmcp 2.2.3, mcp 1.6.0

---

## ⚠️ Important Notes

### API Key Setup
1. **Public Data Portal API Key**: Obtain from [data.go.kr](https://data.go.kr) (URL encoding required)
2. **ECOS API Key**: Obtain from [Bank of Korea ECOS](https://ecos.bok.or.kr)

### Data Management
- All data is automatically cached in `src/mcp_kr_realestate/utils/cache/`
- Cache files are auto-refreshed every 24 hours
- Manual cache deletion/refresh is supported

### Known Limitations
- **Regional Data**: Empty results returned for regions/periods with no transactions
- **API Response Time**: Large data queries may take 1-3 seconds
- **Features in Development**: Real estate-macro correlation analysis, portfolio optimization, AI report generation

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