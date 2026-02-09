# Earnings Document Downloader

Download earnings documents for companies worldwide:
- **Earnings call transcripts**
- **Investor presentations**
- **Press releases / fact sheets**

## Supported Regions

| Region | Source | Coverage |
|--------|--------|----------|
| India | Screener.in + Company IR | All listed companies |
| US | SEC EDGAR | All SEC filers (10-Q, 10-K, 8-K) |
| Japan | TDnet | Major companies |
| Korea | DART | Major companies |
| China | CNINFO | Major companies (SSE, SZSE, HKEX, US-listed) |

## Installation

```bash
cd ~/earnings_downloader
pip install -r requirements.txt
```

## Usage

### CLI

```bash
python cli/app.py
```

Interactive menu:
```
Select region:
  [1] India (indian FY)
  [2] United States (calendar FY)
  [3] Japan (japanese FY)
  [4] Korea (calendar FY)
  [5] China (calendar FY)

Enter company name(s) (comma-separated for multiple)
Companies: Apple, Microsoft

Options:
  [1] Download all documents
  [2] Download transcripts only
  [3] Change output directory
  [4] Change quarters count
  [5] Exit
```

### Web Interface

```bash
uvicorn api.app:app --reload --port 8000
```

Open http://localhost:8000 in your browser.

### API

```bash
# Search companies
curl "http://localhost:8000/api/companies/search?q=Apple&region=us"

# Get available documents
curl "http://localhost:8000/api/documents?company=Apple&region=us&count=5"

# Download documents
curl -X POST "http://localhost:8000/api/downloads" \
  -H "Content-Type: application/json" \
  -d '{"company": "Apple", "region": "us", "count": 5}'
```

## Project Structure

```
earnings_downloader/
├── core/                    # Business logic
│   ├── models.py           # EarningsCall model
│   └── services/           # EarningsService
├── sources/                 # Data sources by region
│   ├── india/              # Screener.in, Company IR
│   ├── us/                 # SEC EDGAR
│   ├── japan/              # TDnet
│   ├── korea/              # DART
│   └── china/              # CNINFO
├── api/                     # FastAPI backend
├── cli/                     # CLI interface
├── web/                     # Web frontend
├── config.py               # Configuration
├── downloader.py           # Async download manager
└── requirements.txt
```

## Fiscal Year Handling

- **India/Japan**: April-March (Q1=Apr-Jun, Q2=Jul-Sep, Q3=Oct-Dec, Q4=Jan-Mar)
- **US/Korea/China**: Calendar year (Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec)

## API Keys Setup

Some regions require free API registration:

### Korea (DART)
1. Register at https://opendart.fss.or.kr/ (free)
2. Get your API key from the dashboard
3. Set environment variable:
   ```bash
   export DART_API_KEY=your_api_key
   ```

### Japan (J-Quants)
1. Register at https://www.jpx-jquants.com/ (free tier available)
2. Set environment variables:
   ```bash
   export TDNET_API_ID=your_email
   export TDNET_API_PASSWORD=your_password
   ```

**No API key needed for:** India (Screener.in), US (SEC EDGAR), China (CNINFO)

## Optional Environment Variables

### BSE Scrip List (India autocomplete)
Provide a local CSV to power company name suggestions in the web UI.

```bash
export BSE_SCRIP_PATH=/home/vignesh/Downloads/SCRIP/BSE_EQ_SCRIP_06022026.csv
```

Expected CSV headers: `Company name`, `symbol`, `ISIN`

## Dependencies

- requests, beautifulsoup4, aiohttp, rich
- pydantic, fastapi, uvicorn

## Adding New Sources

See `CLAUDE.md` for developer documentation on adding new regional sources.
