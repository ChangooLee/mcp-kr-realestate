[한국어](README.md) | English

# MCP Real Estate Investment Analytics Server

![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)

> **⚠️ This project is licensed for non-commercial use only.**
> 
> Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0). Commercial use is strictly prohibited.

![License](https://img.shields.io/github/license/ChangooLee/mcp-kr-realestate)
![GitHub Stars](https://img.shields.io/github/stars/ChangooLee/mcp-kr-realestate)
![GitHub Issues](https://img.shields.io/github/issues/ChangooLee/mcp-kr-realestate)
![GitHub Last Commit](https://img.shields.io/github/last-commit/ChangooLee/mcp-kr-realestate)

Model Context Protocol (MCP) server for advanced real estate investment analytics in Korea. This integration enables secure, contextual AI interactions with Korean real estate data while maintaining data privacy and security.

## Example Usage

Ask your AI assistant to:

- **📊 Transaction Data** - "Get apartment sales transaction data for Gangnam-gu in May 2025"
- **📈 Market Analysis** - "Analyze the officetel rental market in Seocho-dong"
- **🏦 Economic Indicators** - "Search for base interest rate and housing price index"
- **🔍 Data Search** - "Search cached apartment transaction data by complex name"

### Compatibility

| Feature | Support Status | Description |
|---------|---------------|-------------|
| **Apartment Transactions** | ✅ Fully supported | Sales and rental transaction data for apartments |
| **Officetel Transactions** | ✅ Fully supported | Sales and rental transaction data for officetels |
| **Single/Multi-family Homes** | ✅ Fully supported | Sales and rental transaction data for single/multi-family homes |
| **Row Houses** | ✅ Fully supported | Sales and rental transaction data for row houses |
| **Commercial Properties** | ✅ Fully supported | Sales transaction data for commercial properties |
| **Industrial Properties** | ✅ Fully supported | Sales transaction data for factories/warehouses |
| **Land Transactions** | ✅ Fully supported | Sales transaction data for land |
| **ECOS Economic Indicators** | ✅ Fully supported | Bank of Korea ECOS API integration for macroeconomic indicators |
| **Statistical Analysis** | ✅ Fully supported | Comprehensive statistical analysis and reporting |

---

## Quick Start Guide

### 1. Authentication Setup

First, obtain your API keys:

1. **Public Data Portal API Key**: Get from [data.go.kr](https://data.go.kr) (URL encoding required)
2. **ECOS API Key**: Get from [Bank of Korea ECOS](https://ecos.bok.or.kr/api/)

### 2. Installation

```bash
# Clone repository
git clone https://github.com/ChangooLee/mcp-kr-realestate.git
cd mcp-kr-realestate

# [IMPORTANT] Ensure you are using Python 3.10 or higher. See: 'Checking and Installing Python 3.10+' below.

# Create virtual environment
python3.10 -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)

# Install package
python3 -m pip install --upgrade pip
pip install -e .
```

---

## Checking and Installing Python 3.10+

# Check Python version (must be 3.10 or higher)
python3 --version

# If your Python version is lower than 3.10, follow the instructions below to install Python 3.10 or higher:

### macOS
- Download the latest Python installer from the official website: https://www.python.org/downloads/macos/
- Or, if you use Homebrew:
  ```sh
  brew install python@3.10
  ```
  After installation, you may need to use `python3.10` instead of `python3`.

### Windows
- Download and run the latest Python installer from: https://www.python.org/downloads/windows/
- During installation, make sure to check "Add Python to PATH".
- After installation, restart your terminal and use `python` or `python3`.

### Linux (Ubuntu/Debian)
- Update package list and install Python 3.10:
  ```sh
  sudo apt update
  sudo apt install python3.10 python3.10-venv python3.10-distutils
  ```
- You may need to use `python3.10` instead of `python3`.

### Linux (Fedora/CentOS/RHEL)
- Install Python 3.10:
  ```sh
  sudo dnf install python3.10
  ```

---

## IDE Integration

MCP Real Estate Investment Analytics Server is designed to be used with AI assistants through IDE integration.

### Claude Desktop Configuration

1. Click hamburger menu (☰) > Settings > Developer > "Edit Config" button
2. Add the following configuration:

```json
{
  "mcpServers": {
    "mcp-kr-realestate": {
      "command": "YOUR_LOCATION/.venv/bin/mcp-kr-realestate",
      "env": {
        "PUBLIC_DATA_API_KEY": "your-api-key-here",
        "PUBLIC_DATA_API_KEY_ENCODED": "your-url-encoded-api-key-here",
        "ECOS_API_KEY": "your-ecos-api-key-here",
        "HOST": "0.0.0.0",
        "PORT": "8001",
        "TRANSPORT": "stdio",
        "LOG_LEVEL": "INFO",
        "MCP_SERVER_NAME": "mcp-kr-realestate"
      }
    }
  }
}
```

### Streamable HTTP Configuration (Optional)

You can also run with streamable-http using HTTP transport:

```json
{
  "mcpServers": {
    "mcp-kr-realestate": {
      "command": "YOUR_LOCATION/.venv/bin/mcp-kr-realestate",
      "env": {
        "PUBLIC_DATA_API_KEY": "your-api-key-here",
        "PUBLIC_DATA_API_KEY_ENCODED": "your-url-encoded-api-key-here",
        "ECOS_API_KEY": "your-ecos-api-key-here",
        "HOST": "0.0.0.0",
        "PORT": "9001",
        "TRANSPORT": "streamable-http",
        "LOG_LEVEL": "INFO",
        "MCP_SERVER_NAME": "mcp-kr-realestate"
      }
    }
  }
}
```

> [!NOTE]
> - When `TRANSPORT="streamable-http"` is set, the server runs with streamable-http
> - Endpoint: `http://HOST:PORT/mcp`

> [!NOTE]
> - `YOUR_LOCATION`: Replace with the actual path where your virtual environment is installed
> - `your-api-key-here`: Replace with your Public Data Portal API key (both decoded and URL-encoded versions)
> - `your-ecos-api-key-here`: Replace with your ECOS API key

### Environment Variables

- `PUBLIC_DATA_API_KEY`: Your Public Data Portal API key (decoded)
- `PUBLIC_DATA_API_KEY_ENCODED`: Your Public Data Portal API key (URL-encoded)
- `ECOS_API_KEY`: Your Bank of Korea ECOS API key
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8001)
- `TRANSPORT`: Transport method (stdio recommended, set to streamable-http for HTTP transport support)
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)
- `MCP_SERVER_NAME`: Server name

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

## Troubleshooting & Debugging

### Common Issues

- **Authentication Failures**:
  - Check if your API key is valid and active
  - Verify your API key has the necessary permissions
  - For Public Data Portal API key, ensure both decoded and URL-encoded versions are set
  - Check if you've exceeded the API rate limit

- **Data Access Issues**:
  - Some data may require additional permissions
  - Certain data might have delayed access (up to 24 hours)
  - Check if the region code is correct (use get_region_codes to verify)

- **Connection Problems**:
  - Verify your internet connection
  - Check if the Public API service is available
  - Ensure your firewall isn't blocking the connection

### Debugging Tools

```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG

# Test server directly
python -m mcp_kr_realestate.server

# Test in virtual environment
source .venv/bin/activate
mcp-kr-realestate
```

---

## Security

- Never share your API key
- Keep `.env` files secure and private
- Use appropriate rate limiting
- Monitor your API usage
- Store sensitive data in environment variables

---

## Supported Platforms

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
   - Both decoded and URL-encoded versions must be set
2. **ECOS API Key**: Obtain from [Bank of Korea ECOS](https://ecos.bok.or.kr/api/)

### Data Management

- All data is automatically cached in `src/mcp_kr_realestate/utils/cache/`
- Cache files are auto-refreshed every 24 hours
- Manual cache deletion/refresh is supported

### Known Limitations

- **Regional Data**: Empty results returned for regions/periods with no transactions
- **API Response Time**: Large data queries may take 1-3 seconds
- **Features in Development**: Real estate-macro correlation analysis, portfolio optimization, AI report generation

---

## Contributing

We welcome contributions! If you'd like to contribute:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## License

This project is licensed under the [CC BY-NC 4.0 (Non-Commercial Use Only)](https://creativecommons.org/licenses/by-nc/4.0/) license.

- **Use is permitted only for non-commercial, personal, academic/research, or non-profit purposes.**
- **Any use by for-profit companies, commercial services, or in any revenue-generating activity is strictly prohibited.**
- If you are unsure whether your use is permitted, please contact the author (Changoo Lee).
- See the LICENSE file and the link above for full details.

> **한국어:**
> 본 프로젝트는 CC BY-NC 4.0 라이선스 하에 배포되며, 비상업적, 개인, 연구/학습, 비영리 목적에 한해 사용 가능합니다. 영리기업, 상업적 서비스, 수익 창출 목적의 사용은 엄격히 금지됩니다. 자세한 내용은 LICENSE 파일을 참고하세요.

---

**Project Maintainer**: Changoo Lee  
**Contact**: lchangoo@gmail.com  
**GitHub**: https://github.com/ChangooLee/mcp-kr-realestate  
**Blog**: https://changoo.tech  
**LinkedIn**: https://linkedin.com/in/changoo-lee  

**Note**: This project is an analytical tool using public APIs. The final responsibility for investment decisions lies with the user. Please consult with professionals when making actual investments.

**⚠️ 2025 Major Changes**: Some API service structure changes may require code modifications. See [Change Log](https://github.com/ChangooLee/mcp-kr-realestate/blob/main/CHANGELOG.md) for details.
