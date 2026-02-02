"""Screener.in data source for earnings call transcripts."""

import re
import requests
from bs4 import BeautifulSoup
from typing import List, Optional
from urllib.parse import urljoin, quote

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from utils import EarningsCall, normalize_company_name, parse_quarter_year


class ScreenerSource:
    """Fetches earnings call data from Screener.in."""

    BASE_URL = "https://www.screener.in"
    SEARCH_URL = "https://www.screener.in/api/company/search/"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })

    def search_company(self, company_name: str) -> Optional[str]:
        """Search for company and return its page URL."""
        normalized = normalize_company_name(company_name)
        try:
            resp = self.session.get(
                self.SEARCH_URL,
                params={"q": normalized},
                timeout=config.request_timeout
            )
            resp.raise_for_status()
            results = resp.json()

            if not results:
                return None

            # Return first match
            first = results[0]
            return urljoin(self.BASE_URL, first.get("url", ""))

        except Exception as e:
            print(f"  Search error: {e}")
            return None

    def get_earnings_calls(
        self,
        company_name: str,
        count: int = 4,
        include_presentations: bool = False
    ) -> List[EarningsCall]:
        """Get earnings call documents for a company."""
        calls = []

        # Search for company
        company_url = self.search_company(company_name)
        if not company_url:
            print(f"  Company not found on Screener.in: {company_name}")
            return calls

        try:
            # Fetch company page
            resp = self.session.get(company_url, timeout=config.request_timeout)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Get actual company name from page
            name_elem = soup.select_one("h1.margin-0")
            actual_name = name_elem.text.strip() if name_elem else company_name

            # Find concalls section
            concall_section = self._find_concall_section(soup)
            if not concall_section:
                print(f"  No concalls section found for {company_name}")
                return calls

            # Parse concall entries
            entries = self._parse_concall_entries(concall_section, actual_name, include_presentations)
            calls.extend(entries)

        except Exception as e:
            print(f"  Error fetching from Screener.in: {e}")

        # Apply limit based on quarters
        return self._limit_by_quarter(calls, count)

    def _find_concall_section(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        """Find the concalls/documents section."""
        # Primary: find the documents section by ID
        doc_section = soup.find(id="documents")
        if doc_section:
            return doc_section

        # Fallback: look for section with document-related ID
        doc_section = soup.find("section", {"id": re.compile(r"document|concall", re.I)})
        if doc_section:
            return doc_section

        # Try finding by class names
        for section in soup.find_all(["div", "section"]):
            classes = section.get("class", [])
            if any("concall" in c.lower() or "document" in c.lower() for c in classes):
                return section

        # Last resort: find parent of BSE/NSE PDF links
        all_links = soup.find_all("a", href=re.compile(r"(bseindia|nseindia).*\.pdf", re.I))
        if all_links:
            return all_links[0].find_parent("section") or all_links[0].find_parent("div")

        return None

    def _parse_concall_entries(
        self,
        section: BeautifulSoup,
        company_name: str,
        include_presentations: bool
    ) -> List[EarningsCall]:
        """Parse earnings call entries from section."""
        calls = []
        seen_urls = set()

        # Month to quarter mapping (Indian financial year: Apr-Mar)
        month_to_quarter = {
            "jan": ("Q3", lambda y: f"FY{(int(y) % 100):02d}"),
            "feb": ("Q3", lambda y: f"FY{(int(y) % 100):02d}"),
            "mar": ("Q4", lambda y: f"FY{(int(y) % 100):02d}"),
            "apr": ("Q4", lambda y: f"FY{(int(y) % 100):02d}"),
            "may": ("Q1", lambda y: f"FY{((int(y) + 1) % 100):02d}"),
            "jun": ("Q1", lambda y: f"FY{((int(y) + 1) % 100):02d}"),
            "jul": ("Q1", lambda y: f"FY{((int(y) + 1) % 100):02d}"),
            "aug": ("Q2", lambda y: f"FY{((int(y) + 1) % 100):02d}"),
            "sep": ("Q2", lambda y: f"FY{((int(y) + 1) % 100):02d}"),
            "oct": ("Q2", lambda y: f"FY{((int(y) + 1) % 100):02d}"),
            "nov": ("Q3", lambda y: f"FY{((int(y) + 1) % 100):02d}"),
            "dec": ("Q3", lambda y: f"FY{((int(y) + 1) % 100):02d}"),
        }

        def extract_date_info(text: str) -> tuple[str, str]:
            """Extract quarter and fiscal year from text like 'Jan 2026' or 'Oct 2025'."""
            # Try Q format first
            q_match = re.search(r'Q([1-4])\s*(?:FY)?(\d{2,4})', text, re.IGNORECASE)
            if q_match:
                quarter = f"Q{q_match.group(1)}"
                year_str = q_match.group(2)
                year = f"FY{year_str}" if len(year_str) == 2 else f"FY{int(year_str) % 100:02d}"
                return quarter, year

            # Try month-year format
            month_match = re.search(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+(\d{4})', text, re.IGNORECASE)
            if month_match:
                month = month_match.group(1).lower()
                year = month_match.group(2)
                if month in month_to_quarter:
                    quarter, fy_func = month_to_quarter[month]
                    return quarter, fy_func(year)

            return "", ""

        # Find transcript links
        transcript_links = section.find_all("a", string=re.compile(r"transcript", re.I))
        for link in transcript_links:
            href = link.get("href", "")
            if not href or href in seen_urls:
                continue
            seen_urls.add(href)

            # Get context from parent li element
            parent_li = link.find_parent("li")
            context = parent_li.get_text(" ", strip=True) if parent_li else ""
            quarter, year = extract_date_info(context)

            if not quarter:
                quarter, year = "Unknown", ""

            full_url = href if href.startswith("http") else urljoin(self.BASE_URL, href)

            calls.append(EarningsCall(
                company=company_name,
                quarter=quarter,
                year=year,
                doc_type="transcript",
                url=full_url,
                source="screener"
            ))

        # Find presentation links if requested
        if include_presentations:
            ppt_links = section.find_all("a", string=re.compile(r"ppt|presentation", re.I))
            for link in ppt_links:
                href = link.get("href", "")
                if not href or href in seen_urls:
                    continue
                seen_urls.add(href)

                parent_li = link.find_parent("li")
                context = parent_li.get_text(" ", strip=True) if parent_li else ""
                quarter, year = extract_date_info(context)

                if not quarter:
                    quarter, year = "Unknown", ""

                full_url = href if href.startswith("http") else urljoin(self.BASE_URL, href)

                calls.append(EarningsCall(
                    company=company_name,
                    quarter=quarter,
                    year=year,
                    doc_type="presentation",
                    url=full_url,
                    source="screener"
                ))

        return calls

    def _limit_by_quarter(self, calls: List[EarningsCall], count: int) -> List[EarningsCall]:
        """Limit results to specified number of quarters, keeping both types."""
        # Group by quarter
        from collections import defaultdict
        by_quarter = defaultdict(list)

        for call in calls:
            quarter_key = (call.quarter, call.year)
            by_quarter[quarter_key].append(call)

        # Sort quarters (most recent first based on year then quarter)
        def quarter_sort_key(q):
            quarter, year = q
            # Extract numeric parts
            q_num = int(quarter[1]) if quarter.startswith("Q") else 0
            y_num = int(year[2:]) if year.startswith("FY") else 0
            return (-y_num, -q_num)

        sorted_quarters = sorted(by_quarter.keys(), key=quarter_sort_key)

        # Take top N quarters with all their documents
        result = []
        for quarter_key in sorted_quarters[:count]:
            result.extend(by_quarter[quarter_key])

        return result
