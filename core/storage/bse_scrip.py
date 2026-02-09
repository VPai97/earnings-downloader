"""Load and search BSE scrip list for company suggestions."""

import csv
import logging
import os
from typing import Dict, List, Optional

from core.models import normalize_company_name


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
        by_name: Dict[str, Dict[str, str]] = {}
        aliases_by_name: Dict[str, set[str]] = {}
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
                    name_norm = normalize_company_name(name).lower().strip()
                    if not name_norm:
                        name_norm = name.lower().strip()
                    symbol_norm = symbol.lower().strip()
                    raw_norm = name.lower().strip()

                    if name_norm not in by_name:
                        entry = {
                            "name": name,
                            "symbol": symbol,
                            "isin": isin,
                            "name_norm": name_norm,
                            "symbol_norm": symbol_norm,
                        }
                        by_name[name_norm] = entry
                        aliases_by_name[name_norm] = {name_norm, raw_norm}
                    else:
                        entry = by_name[name_norm]
                        aliases_by_name[name_norm].add(raw_norm)
                        aliases_by_name[name_norm].add(name_norm)

                        # Prefer keeping a symbol/isin if the existing entry lacks it
                        if not entry.get("symbol") and symbol:
                            entry["symbol"] = symbol
                            entry["symbol_norm"] = symbol_norm
                        if not entry.get("isin") and isin:
                            entry["isin"] = isin

            # Build final entries list with aliases for matching
            for name_norm, entry in by_name.items():
                entry["aliases"] = tuple(aliases_by_name.get(name_norm, {name_norm}))
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
            aliases = entry.get("aliases", (entry["name_norm"],))
            name_match = any(alias.startswith(normalized_query) for alias in aliases)
            symbol_match = entry["symbol_norm"] and entry["symbol_norm"].startswith(normalized_query)
            if name_match or symbol_match:
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
