"""Utility functions for Earnings Call Downloader.

This module re-exports from core.models for backwards compatibility.
"""

# Re-export everything from core.models for backwards compatibility
from core.models import (
    EarningsCall,
    normalize_company_name,
    parse_quarter_year,
    deduplicate_calls,
)

__all__ = [
    "EarningsCall",
    "normalize_company_name",
    "parse_quarter_year",
    "deduplicate_calls",
]
