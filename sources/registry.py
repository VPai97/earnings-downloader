"""Registry for managing earnings document sources by region."""

from typing import Dict, List, Optional
from .base import BaseSource, Region


class SourceRegistry:
    """Registry for regional sources."""

    _sources: Dict[Region, List[BaseSource]] = {}

    @classmethod
    def register(cls, source: BaseSource) -> None:
        """Register a source for its region."""
        if source.region not in cls._sources:
            cls._sources[source.region] = []

        # Avoid duplicate registrations
        existing_names = [s.source_name for s in cls._sources[source.region]]
        if source.source_name not in existing_names:
            cls._sources[source.region].append(source)
            # Sort by priority (lower = higher priority)
            cls._sources[source.region].sort(key=lambda s: s.priority)

    @classmethod
    def get_sources(cls, region: Region) -> List[BaseSource]:
        """Get all sources for a region, sorted by priority."""
        return cls._sources.get(region, [])

    @classmethod
    def get_all_sources(cls) -> List[BaseSource]:
        """Get all registered sources across all regions."""
        all_sources = []
        for sources in cls._sources.values():
            all_sources.extend(sources)
        return all_sources

    @classmethod
    def get_regions(cls) -> List[Region]:
        """Get all regions that have registered sources."""
        return list(cls._sources.keys())

    @classmethod
    def get_source_by_name(cls, name: str) -> Optional[BaseSource]:
        """Find a source by its name."""
        for sources in cls._sources.values():
            for source in sources:
                if source.source_name == name:
                    return source
        return None

    @classmethod
    def clear(cls) -> None:
        """Clear all registered sources (mainly for testing)."""
        cls._sources = {}
