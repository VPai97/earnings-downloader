"""Company search API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from core.services import EarningsService
from sources.base import Region


router = APIRouter(prefix="/api/companies", tags=["companies"])
service = EarningsService()


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
