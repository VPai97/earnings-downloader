"""Data models for earnings downloader."""

import re
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class EarningsCall(BaseModel):
    """Represents an earnings call document."""

    company: str = Field(..., description="Company name")
    quarter: str = Field(..., description="Quarter (e.g., 'Q3', 'Q4')")
    year: str = Field(..., description="Fiscal year (e.g., 'FY26', '2025')")
    doc_type: str = Field(..., description="Document type: transcript, presentation, press_release")
    url: str = Field(..., description="Download URL")
    source: str = Field(..., description="Source name: screener, company_ir, edgar, etc.")
    date: Optional[datetime] = Field(None, description="Document date if available")

    class Config:
        frozen = True  # Make hashable for deduplication

    def get_filename(self) -> str:
        """Generate filename for this document."""
        ext = self._get_extension()
        safe_company = re.sub(r'[^\w\s-]', '', self.company)
        safe_company = safe_company.strip().replace(' ', '_')[:50]
        return f"{safe_company}_{self.quarter}{self.year}_{self.doc_type}{ext}"

    def _get_extension(self) -> str:
        """Determine file extension from URL or doc type."""
        url_lower = self.url.lower()
        if '.pdf' in url_lower:
            return '.pdf'
        elif '.ppt' in url_lower or '.pptx' in url_lower:
            return '.pptx'
        elif '.mp3' in url_lower or '.wav' in url_lower:
            return '.mp3'
        elif self.doc_type == 'presentation':
            return '.pdf'
        return '.pdf'


def normalize_company_name(name: str) -> str:
    """Normalize company name for searching."""
    suffixes = [' Ltd', ' Limited', ' Ltd.', ' Inc', ' Inc.', ' Corp', ' Corporation']
    normalized = name.strip()
    for suffix in suffixes:
        if normalized.lower().endswith(suffix.lower()):
            normalized = normalized[:-len(suffix)]
    return normalized.strip()


def parse_quarter_year(text: str) -> tuple[Optional[str], Optional[str]]:
    """Extract quarter and year from text like 'Q3FY26' or 'Q3 2025'."""
    match = re.search(r'Q([1-4])\s*(?:FY)?(\d{2,4})', text, re.IGNORECASE)
    if match:
        quarter = f"Q{match.group(1)}"
        year_str = match.group(2)
        if len(year_str) == 2:
            year = f"FY{year_str}"
        else:
            year = year_str
        return quarter, year
    return None, None


def deduplicate_calls(calls: list[EarningsCall]) -> list[EarningsCall]:
    """Remove duplicate earnings calls, preferring certain sources."""
    seen = {}  # (company, quarter, year, doc_type) -> call
    # Prefer company IR pages over aggregators
    source_priority = {
        "company_ir": 0,
        "screener": 1,
        "edgar": 2,
        "tdnet": 3,
        "dart": 4,
        "cninfo": 5,
        "trendlyne": 6,
        "bse": 7
    }

    for call in calls:
        key = (call.company.lower(), call.quarter, call.year, call.doc_type)
        if key not in seen:
            seen[key] = call
        else:
            existing = seen[key]
            if source_priority.get(call.source, 99) < source_priority.get(existing.source, 99):
                seen[key] = call

    return list(seen.values())
