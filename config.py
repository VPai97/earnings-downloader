"""Configuration for Earnings Call Downloader."""

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Config:
    """Configuration settings."""
    output_dir: str = "./downloads"
    quarters_per_company: int = 5

    # Document types to download
    include_transcripts: bool = True
    include_presentations: bool = True
    include_press_releases: bool = True

    # Request settings
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0

    # User agent for requests
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # Sources to try (in order)
    sources: List[str] = field(default_factory=lambda: ["screener"])

    # API Keys (loaded from environment variables)
    # Korea DART: Register at https://opendart.fss.or.kr/ (free)
    dart_api_key: Optional[str] = field(default_factory=lambda: os.environ.get("DART_API_KEY"))

    # Japan TDnet: Register at https://www.jpx-jquants.com/ (free tier available)
    tdnet_api_id: Optional[str] = field(default_factory=lambda: os.environ.get("TDNET_API_ID"))
    tdnet_api_password: Optional[str] = field(default_factory=lambda: os.environ.get("TDNET_API_PASSWORD"))

    def get_output_path(self, company: str) -> str:
        """Get output directory for a company."""
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in company)
        safe_name = safe_name.strip().replace(" ", "_")
        path = os.path.join(self.output_dir, safe_name)
        os.makedirs(path, exist_ok=True)
        return path


# Global config instance
config = Config()
