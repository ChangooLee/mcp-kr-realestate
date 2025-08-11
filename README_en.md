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

| Tool | User-Focused Function | Input Information | What You Get |
|------|----------------------|------------------|--------------|
| **get_region_codes** | Find regional codes needed for real estate data queries | Region name (e.g., "Gangnam-gu", "Seocho-dong") | List of legal district codes for the area |
| **get_apt_trade_data** | Get apartment sales transaction status for specific area | Region code, query month | Detailed transaction records: sales prices, areas, transaction dates by apartment |
| **get_apt_rent_data** | Get apartment rental transaction status for specific area | Region code, query month | Detailed transaction records: jeonse/monthly rent, areas, contract dates by apartment |
| **get_officetel_trade_data** | Get officetel sales transaction status for specific area | Region code, query month | Detailed transaction records: sales prices, areas, transaction dates by officetel |
| **get_officetel_rent_data** | Get officetel rental transaction status for specific area | Region code, query month | Detailed transaction records: jeonse/monthly rent, areas, contract dates by officetel |
| **get_single_detached_house_trade_data** | Get single/multi-family house sales transaction status for specific area | Region code, query month | Detailed transaction records: sales prices, areas, transaction dates by house |
| **get_single_detached_house_rent_data** | Get single/multi-family house rental transaction status for specific area | Region code, query month | Detailed transaction records: jeonse/monthly rent, areas, contract dates by house |
| **get_row_house_trade_data** | Get row house sales transaction status for specific area | Region code, query month | Detailed transaction records: sales prices, areas, transaction dates by row house |
| **get_row_house_rent_data** | Get row house rental transaction status for specific area | Region code, query month | Detailed transaction records: jeonse/monthly rent, areas, contract dates by row house |
| **get_commercial_property_trade_data** | Get commercial real estate sales transaction status for specific area | Region code, query month | Detailed transaction records: sales prices, areas, usage, transaction dates by commercial property |
| **get_industrial_property_trade_data** | Get factory/warehouse sales transaction status for specific area | Region code, query month | Detailed transaction records: sales prices, areas, usage, transaction dates by industrial property |
| **get_land_trade_data** | Get land sales transaction status for specific area | Region code, query month | Detailed transaction records: sales prices, areas, land type, transaction dates by land |
| **get_transaction_cache_data** | Search previously collected transaction data with specific conditions | Asset type, region, period, search criteria | Transaction records matching criteria + basic statistics |

### 📊 Transaction Data Analysis Tools (11 tools)

| Tool | User-Focused Function | Input Information | What You Get |
|------|----------------------|------------------|--------------|
| **analyze_apartment_trade** | Generate apartment sales market analysis report | Transaction data file | Average/highest/lowest sales prices, complex rankings, price per pyeong analysis, representative transaction cases |
| **analyze_apartment_rent** | Generate apartment rental market analysis report | Transaction data file | Jeonse/monthly rent market status, average deposit/rent, rental comparison by complex |
| **analyze_officetel_trade** | Generate officetel sales market analysis report | Transaction data file | Average/highest/lowest sales prices, building rankings, price per pyeong analysis, representative transaction cases |
| **analyze_officetel_rent** | Generate officetel rental market analysis report | Transaction data file | Jeonse/monthly rent market status, average deposit/rent, rental comparison by building |
| **analyze_single_detached_house_trade** | Generate single/multi-family house sales market analysis report | Transaction data file | Average/highest/lowest sales prices, price analysis by gross floor area, representative transaction cases |
| **analyze_single_detached_house_rent** | Generate single/multi-family house rental market analysis report | Transaction data file | Jeonse/monthly rent market status, average deposit/rent, rental comparison by area |
| **analyze_row_house_trade** | Generate row house sales market analysis report | Transaction data file | Average/highest/lowest sales prices, complex rankings, price analysis by exclusive area |
| **analyze_row_house_rent** | Generate row house rental market analysis report | Transaction data file | Jeonse/monthly rent market status, average deposit/rent, rental comparison by complex |
| **analyze_commercial_property_trade** | Generate commercial real estate sales market analysis report | Transaction data file | Price analysis by use type/location, building feature comparison, investment perspective analysis |
| **analyze_industrial_property_trade** | Generate factory/warehouse sales market analysis report | Transaction data file | Price analysis by use type/location, building scale comparison, investment perspective analysis |
| **analyze_land_trade** | Generate land sales market analysis report | Transaction data file | Land price analysis by land type/location, price per pyeong comparison by area, development potential analysis |

### 🏦 ECOS/Macro Indicator Tools (6 tools)

| Tool | User-Focused Function | Input Information | What You Get |
|------|----------------------|------------------|--------------|
| **get_ecos_statistic_table_list** | Check all statistical tables provided by Bank of Korea | Query range, specific stat code (optional) | List of available economic statistics (GDP, inflation, interest rates, etc.) |
| **get_ecos_statistic_word** | Find accurate meanings of economic statistical terms | Search term, query range | Definitions and explanations of economic terminology |
| **get_ecos_statistic_item_list** | Check detailed items of specific statistical table | Statistical table code, query range | Detailed categories and item list of the statistics |
| **get_ecos_statistic_search** | Get time series data of desired economic indicators | Stat code, cycle, period, detailed items | Actual economic indicator values (monthly/quarterly/annual data) |
| **get_ecos_key_statistic_list** | Check status of Korea's core 100 economic indicators | Query range | Current values and summary information of major economic indicators |
| **search_realestate_indicators** | Quick search for economic indicators needed for real estate investment | Keywords (e.g., "base rate", "housing prices") | Latest figures, units, and announcement dates of related indicators |

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