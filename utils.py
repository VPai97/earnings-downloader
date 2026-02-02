"""Utility functions for Earnings Call Downloader."""

import re
from typing import Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class EarningsCall:
    """Represents an earnings call document."""
    company: str
    quarter: str  # e.g., "Q3", "Q4"
    year: str     # e.g., "FY26", "2025"
    doc_type: str  # "transcript", "presentation", "recording"
    url: str
    source: str   # "screener", "trendlyne", etc.
    date: Optional[datetime] = None

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
    # Remove common suffixes
    suffixes = [' Ltd', ' Limited', ' Ltd.', ' Inc', ' Inc.', ' Corp', ' Corporation']
    normalized = name.strip()
    for suffix in suffixes:
        if normalized.lower().endswith(suffix.lower()):
            normalized = normalized[:-len(suffix)]
    return normalized.strip()


def parse_quarter_year(text: str) -> tuple[Optional[str], Optional[str]]:
    """Extract quarter and year from text like 'Q3FY26' or 'Q3 2025'."""
    # Pattern: Q1-Q4 followed by FY or year
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
    source_priority = {"screener": 0, "trendlyne": 1, "bse": 2}

    for call in calls:
        key = (call.company.lower(), call.quarter, call.year, call.doc_type)
        if key not in seen:
            seen[key] = call
        else:
            existing = seen[key]
            if source_priority.get(call.source, 99) < source_priority.get(existing.source, 99):
                seen[key] = call

    return list(seen.values())
