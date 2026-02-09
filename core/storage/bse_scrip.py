"""Load and search BSE scrip list for company suggestions."""

import csv
import logging
import os
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)


class BseScripStore:
    """In-memory cache for BSE scrip list."""

    def __init__(self, path: str):
        self.path = path
        self._entries: List[Dict[str, str]] = []
        self._mtime: Optional[float] = None

    def _normalize_row(self, row: Dict[str, str]) -> Dict[str, str]:
        normalized: Dict[str, str] = {}
        for key, value in row.items():
            if key is None:
                continue
            normalized[key.strip().lower()] = (value or "").strip()
        return normalized

    def _load_if_needed(self) -> bool:
        if not os.path.exists(self.path):
            if self._entries:
                logger.warning("BSE scrip file not found at %s", self.path)
            self._entries = []
            self._mtime = None
            return False

        mtime = os.path.getmtime(self.path)
        if self._mtime == mtime and self._entries:
            return True

        entries: List[Dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        try:
            with open(self.path, "r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    normalized = self._normalize_row(row)
                    name = normalized.get("company name") or normalized.get("name") or ""
                    symbol = normalized.get("symbol") or ""
                    isin = normalized.get("isin") or ""
                    if not name:
                        continue
                    name_norm = name.lower().strip()
                    symbol_norm = symbol.lower().strip()
                    key = (name_norm, symbol_norm)
                    if key in seen:
                        continue
                    seen.add(key)
                    entry = {
                        "name": name,
                        "symbol": symbol,
                        "isin": isin,
                        "name_norm": name_norm,
                        "symbol_norm": symbol_norm,
                    }
                    entries.append(entry)
        except Exception as exc:
            logger.exception("Failed to load BSE scrip list: %s", exc)
            self._entries = []
            self._mtime = None
            return False

        entries.sort(key=lambda item: item["name_norm"])
        self._entries = entries
        self._mtime = mtime
        return True

    def suggest(self, query: str, limit: int = 20) -> List[Dict[str, str]]:
        if not query:
            return []

        if not self._load_if_needed():
            return []

        normalized_query = query.strip().lower()
        if not normalized_query:
            return []

        matches: List[Dict[str, str]] = []
        seen_labels: set[str] = set()
        for entry in self._entries:
            if entry["name_norm"].startswith(normalized_query) or (
                entry["symbol_norm"] and entry["symbol_norm"].startswith(normalized_query)
            ):
                label = entry["name"]
                if entry["symbol"]:
                    label = f"{entry['name']} ({entry['symbol']})"
                if label in seen_labels:
                    continue
                seen_labels.add(label)
                matches.append({
                    "name": entry["name"],
                    "symbol": entry["symbol"],
                    "isin": entry["isin"],
                    "label": label,
                })
                if len(matches) >= limit:
                    break

        return matches
