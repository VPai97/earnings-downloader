# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the CLI
python cli/app.py

# Run the web server
uvicorn api.app:app --reload --port 8000

# Install dependencies
pip install -r requirements.txt
```

No tests exist yet. No build step required.

## Architecture

This tool downloads earnings documents (transcripts, presentations, press releases) for companies worldwide.

### Project Structure

```
earnings_downloader/
├── core/                    # Business logic (shared)
│   ├── models.py           # EarningsCall Pydantic model
│   └── services/
│       └── earnings.py     # EarningsService - main business logic
├── sources/                 # Data sources by region
│   ├── base.py             # BaseSource ABC, Region enum
│   ├── registry.py         # SourceRegistry for managing sources
│   ├── india/              # Screener.in + Company IR pages
│   ├── us/                 # SEC EDGAR
│   ├── japan/              # TDnet
│   ├── korea/              # DART
│   └── china/              # CNINFO
├── api/                     # FastAPI backend
│   ├── app.py              # Main app
│   └── routes/             # API endpoints
├── cli/                     # CLI interface
│   └── app.py              # Interactive CLI
├── web/                     # Frontend
│   ├── index.html
│   ├── app.js
│   └── style.css
├── config.py               # Configuration
├── downloader.py           # Async download manager
└── utils.py                # Backwards-compatible exports
```

### Key Design Decisions

- **Pluggable sources**: Each region has its own source(s) extending `BaseSource`. Auto-registration via `SourceRegistry`.
- **Service layer**: `EarningsService` provides shared business logic for both CLI and API.
- **Fiscal year handling**: India/Japan use Apr-Mar FY; US/Korea/China use calendar year.
- **Source priority**: company_ir > screener > edgar > tdnet > dart > cninfo for deduplication.

### Adding New Sources

1. Create `sources/{region}/{source_name}.py`
2. Extend `BaseSource` with required attributes (region, fiscal_year_type, source_name, priority)
3. Implement `search_company()` and `get_earnings_calls()`
4. Call `SourceRegistry.register(YourSource())` at module level
5. Import in `sources/{region}/__init__.py` and `sources/__init__.py`

### API Endpoints

- `GET /api/companies/regions` - List available regions
- `GET /api/companies/search?q=&region=` - Search companies
- `GET /api/documents?company=&region=&count=&types=` - Get documents
- `POST /api/downloads` - Download documents to server
