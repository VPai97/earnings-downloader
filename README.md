# Earnings Document Downloader

Interactive CLI tool to download earnings documents for Indian companies:
- **Earnings call transcripts**
- **Investor presentations**
- **Press releases / fact sheets**

## Installation

```bash
cd ~/earnings_downloader
pip install -r requirements.txt
```

## Usage

```bash
python main.py
# or if alias is set up:
earnings
```

### Interactive Menu

```
Enter company name(s) (comma-separated for multiple)
Companies: Reliance Industries, TCS

Options:
  [1] Download all documents (transcripts + presentations + press releases)
  [2] Download transcripts only
  [3] Change output directory (current: ./downloads)
  [4] Change quarters count (current: 5)
  [5] Exit
```

## Features

- **Checks company IR websites first**, then falls back to Screener.in
- Downloads **5 most recent quarters** by default (configurable)
- Downloads **3 document types**: transcripts, presentations, press releases
- Known IR pages for 25+ major Indian companies
- Organizes files by company in subdirectories
- Progress display with rich formatting
- Handles Indian financial year quarters:
  - Q1: Apr-Jun
  - Q2: Jul-Sep
  - Q3: Oct-Dec
  - Q4: Jan-Mar

## Output Structure

```
./downloads/
├── Reliance_Industries_Ltd/
│   ├── Reliance_Industries_Ltd_Q3FY26_transcript.pdf
│   ├── Reliance_Industries_Ltd_Q3FY26_presentation.pdf
│   ├── Reliance_Industries_Ltd_Q3FY26_press_release.pdf
│   └── ... (5 quarters worth)
└── Infosys_Ltd/
    └── ...
```

## Project Structure

```
earnings_downloader/
├── main.py           # Interactive CLI entry point
├── config.py         # Configuration settings
├── downloader.py     # Async download manager with retry logic
├── utils.py          # Helpers (naming, deduplication, quarter parsing)
├── requirements.txt  # Python dependencies
└── sources/
    ├── __init__.py
    ├── company_ir.py # Company IR website scraper (primary)
    └── screener.py   # Screener.in scraper (fallback)
```

## Dependencies

- requests
- beautifulsoup4
- aiohttp
- rich

## Quick Access (Alias)

Add to `~/.bashrc` or `~/.zshrc`:

```bash
alias earnings="cd ~/earnings_downloader && python3 main.py"
```

Then run `earnings` from anywhere.

## Data Sources (Priority Order)

1. **Company IR Websites** - Official investor relations pages (checked first)
2. **Screener.in** - Aggregates filings from BSE India (fallback)

Known IR page mappings exist for: Reliance, TCS, Infosys, HDFC Bank, ICICI Bank, Wipro, HCL Tech, Bharti Airtel, Maruti Suzuki, Motherson, Bajaj Finance, Kotak, Axis Bank, ITC, L&T, Sun Pharma, Titan, UltraTech, Nestle India, Power Grid, NTPC, ONGC, SBI, and more.
