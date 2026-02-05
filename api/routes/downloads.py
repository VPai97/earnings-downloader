"""Download API endpoints."""

import os
import tempfile
import zipfile
from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.services import EarningsService
from core.models import EarningsCall
from sources.base import Region
from downloader import Downloader
from config import config


router = APIRouter(prefix="/api", tags=["downloads"])
service = EarningsService()


class DocumentResponse(BaseModel):
    """Earnings document info."""
    company: str
    quarter: str
    year: str
    doc_type: str
    url: str
    source: str
    filename: str


class DownloadRequest(BaseModel):
    """Download request body."""
    company: str
    region: Optional[str] = "india"
    count: int = 5
    include_transcripts: bool = True
    include_presentations: bool = True
    include_press_releases: bool = True


class DownloadResponse(BaseModel):
    """Download response."""
    message: str
    file_count: int
    download_url: Optional[str] = None


@router.get("/documents", response_model=List[DocumentResponse])
async def get_documents(
    company: str = Query(..., description="Company name"),
    region: Optional[str] = Query("india", description="Region (india, us, japan, korea, china)"),
    count: int = Query(5, ge=1, le=20, description="Number of quarters"),
    types: Optional[str] = Query(
        "transcript,presentation,press_release",
        description="Document types (comma-separated)"
    )
):
    """
    Get available earnings documents for a company.

    Returns list of documents with their URLs and metadata.
    """
    region_enum = None
    if region:
        try:
            region_enum = Region(region.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid region: {region}")

    doc_types = [t.strip() for t in types.split(",")] if types else ["transcript"]

    documents = service.get_earnings_documents(
        company,
        region=region_enum,
        count=count,
        include_transcripts="transcript" in doc_types,
        include_presentations="presentation" in doc_types,
        include_press_releases="press_release" in doc_types
    )

    return [
        DocumentResponse(
            company=doc.company,
            quarter=doc.quarter,
            year=doc.year,
            doc_type=doc.doc_type,
            url=doc.url,
            source=doc.source,
            filename=doc.get_filename()
        )
        for doc in documents
    ]


@router.post("/downloads", response_model=DownloadResponse)
async def create_download(request: DownloadRequest):
    """
    Download earnings documents for a company.

    Downloads files to the server and returns a path to access them.
    For a web interface, this creates a zip file that can be downloaded.
    """
    region_enum = None
    if request.region:
        try:
            region_enum = Region(request.region.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid region: {request.region}")

    documents = service.get_earnings_documents(
        request.company,
        region=region_enum,
        count=request.count,
        include_transcripts=request.include_transcripts,
        include_presentations=request.include_presentations,
        include_press_releases=request.include_press_releases
    )

    if not documents:
        raise HTTPException(status_code=404, detail="No documents found for this company")

    # Download to server
    downloader = Downloader()
    output_dir = config.get_output_path(request.company)
    results = downloader.download_sync(documents, output_dir)

    success_count = sum(1 for _, success, _ in results if success)

    return DownloadResponse(
        message=f"Downloaded {success_count} of {len(documents)} files to {output_dir}",
        file_count=success_count,
        download_url=f"/downloads/{os.path.basename(output_dir)}"
    )


@router.get("/downloads/{company_folder}")
async def get_downloaded_files(company_folder: str):
    """
    List downloaded files for a company.
    """
    folder_path = os.path.join(config.output_dir, company_folder)

    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail="Download folder not found")

    files = []
    for f in os.listdir(folder_path):
        filepath = os.path.join(folder_path, f)
        if os.path.isfile(filepath):
            files.append({
                "name": f,
                "size": os.path.getsize(filepath),
                "url": f"/api/downloads/{company_folder}/{f}"
            })

    return {"folder": company_folder, "files": files}


@router.get("/downloads/{company_folder}/{filename}")
async def download_file(company_folder: str, filename: str):
    """
    Download a specific file.
    """
    filepath = os.path.join(config.output_dir, company_folder, filename)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        filepath,
        filename=filename,
        media_type="application/octet-stream"
    )
