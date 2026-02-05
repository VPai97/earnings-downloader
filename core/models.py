"""Data models for earnings downloader."""

import re
from typing import Optional, List, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
from rapidfuzz import fuzz, process


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
    suffixes = [
        ' Ltd', ' Limited', ' Ltd.', ' Inc', ' Inc.', ' Corp', ' Corporation',
        ' Co.', ' Co', ' Company', ' PLC', ' plc', ' NV', ' SA', ' AG', ' SE',
        ' Holdings', ' Group', ' International', ' Intl',
    ]
    normalized = name.strip()
    for suffix in suffixes:
        if normalized.lower().endswith(suffix.lower()):
            normalized = normalized[:-len(suffix)]
    # Remove extra whitespace
    normalized = ' '.join(normalized.split())
    return normalized.strip()


def fuzzy_match_company(
    query: str,
    candidates: List[str],
    threshold: int = 60
) -> List[Tuple[str, int]]:
    """
    Fuzzy match a company name against a list of candidates.

    Args:
        query: Search query
        candidates: List of company names to match against
        threshold: Minimum match score (0-100)

    Returns:
        List of (company_name, score) tuples, sorted by score descending
    """
    if not candidates:
        return []

    normalized_query = normalize_company_name(query).lower()

    # Use rapidfuzz for fuzzy matching
    results = process.extract(
        normalized_query,
        candidates,
        scorer=fuzz.WRatio,  # Weighted ratio handles partial matches well
        limit=10
    )

    # Filter by threshold and return
    return [(name, score) for name, score, _ in results if score >= threshold]


def find_best_company_match(
    query: str,
    company_dict: dict,
    threshold: int = 60
) -> Optional[str]:
    """
    Find the best matching company key from a dictionary.

    Args:
        query: Search query
        company_dict: Dictionary with company names/keys
        threshold: Minimum match score

    Returns:
        Best matching key or None
    """
    candidates = list(company_dict.keys())
    matches = fuzzy_match_company(query, candidates, threshold)

    if matches:
        return matches[0][0]  # Return the best match
    return None


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

    # Priority: lower number = higher priority (preferred)
    # 1. BSE/NSE official filings
    # 2. Company IR pages
    # 3. Aggregators (Screener, Trendlyne, etc.)
    source_priority = {
        "bse": 0,
        "nse": 0,
        "company_ir": 1,
        "screener": 2,
        "trendlyne": 3,
        "edgar": 1,  # Official SEC filings
        "tdnet": 1,  # Official Japan filings
        "dart": 1,   # Official Korea filings
        "cninfo": 1, # Official China filings
    }

    # First pass: deduplicate by URL (exact same document)
    seen_urls = {}
    for call in calls:
        url_key = call.url.lower().rstrip('/')
        if url_key not in seen_urls:
            seen_urls[url_key] = call
        else:
            existing = seen_urls[url_key]
            if source_priority.get(call.source, 99) < source_priority.get(existing.source, 99):
                seen_urls[url_key] = call

    # Second pass: deduplicate by (company, quarter, year, doc_type)
    seen = {}  # (normalized_company, quarter, year, doc_type) -> call
    for call in seen_urls.values():
        # Normalize company name for better matching
        normalized_company = normalize_company_name(call.company).lower()
        key = (normalized_company, call.quarter, call.year, call.doc_type)
        if key not in seen:
            seen[key] = call
        else:
            existing = seen[key]
            if source_priority.get(call.source, 99) < source_priority.get(existing.source, 99):
                seen[key] = call

    return list(seen.values())
