"""Company search API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from config import config
from core.services import EarningsService
from core.storage.bse_scrip import BseScripStore
from sources.base import Region


router = APIRouter(prefix="/api/companies", tags=["companies"])
service = EarningsService()
BSE_SCRIP_STORE = BseScripStore(config.bse_scrip_path)


class CompanySearchResult(BaseModel):
    """Company search result."""
    name: str
    url: str
    source: str
    region: str


class RegionInfo(BaseModel):
    """Region information."""
    id: str
    name: str
    fiscal_year: str
    sources: List[str]


class CompanySuggestion(BaseModel):
    """Company suggestion result."""
    name: str
    symbol: Optional[str] = None
    isin: Optional[str] = None
    label: str


@router.get("/search", response_model=List[CompanySearchResult])
async def search_companies(
    q: str = Query(..., min_length=1, description="Company name to search"),
    region: Optional[str] = Query(None, description="Region to search in (india, us, japan, korea, china)")
):
    """
    Search for companies by name.

    Returns list of matching companies with their IR page URLs and sources.
    """
    region_enum = None
    if region:
        try:
            region_enum = Region(region.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid region: {region}")

    results = service.search_company(q, region=region_enum)
    return results


@router.get("/regions", response_model=List[RegionInfo])
async def list_regions():
    """
    List all available regions with their sources.
    """
    return service.get_available_regions()


@router.get("/suggest", response_model=List[CompanySuggestion])
async def suggest_companies(
    q: str = Query(..., min_length=1, description="Company name to suggest"),
    region: Optional[str] = Query("india", description="Region to search in (india, us, japan, korea, china)"),
    limit: int = Query(20, ge=1, le=50, description="Maximum suggestions to return")
):
    """
    Suggest companies for autocomplete.

    For India, uses the local BSE scrip list. For other regions, uses source search.
    """
    region_value = region.lower() if region else "india"
    try:
        region_enum = Region(region_value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid region: {region}")

    if region_enum == Region.INDIA:
        return BSE_SCRIP_STORE.suggest(q, limit=limit)

    results = service.search_company(q, region=region_enum)
    suggestions: List[CompanySuggestion] = []
    for result in results[:limit]:
        name = result.get("name") or ""
        if not name:
            continue
        suggestions.append(CompanySuggestion(
            name=name,
            symbol=result.get("symbol"),
            isin=result.get("isin"),
            label=name
        ))
    return suggestions
