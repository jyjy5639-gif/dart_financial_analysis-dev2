from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from backend.services.dart_service import DARTService
from backend.api.dependencies import get_dart_service
from shared.schemas import Company, CompanySearchResponse, ErrorResponse
from backend.core.logger import get_backend_logger

logger = get_backend_logger("company")
router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("/list", response_model=CompanySearchResponse)
async def get_company_list(
    force_refresh: bool = Query(False, description="캐시 무시하고 새로 다운로드"),
    dart_service: DARTService = Depends(get_dart_service)
):
    """전체 회사 목록 조회"""
    try:
        logger.info(f"Fetching company list (force_refresh={force_refresh})")
        companies = dart_service.get_corp_list(force_refresh=force_refresh)
        logger.info(f"Successfully fetched {len(companies)} companies")
        return {
            "companies": companies,
            "total": len(companies)
        }
    except Exception as e:
        logger.error(f"Failed to fetch company list: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=CompanySearchResponse)
async def search_companies(
    keyword: str = Query(..., min_length=1, description="검색 키워드"),
    dart_service: DARTService = Depends(get_dart_service)
):
    """회사 검색"""
    try:
        logger.info(f"Searching companies with keyword: '{keyword}'")
        companies = dart_service.search_companies(keyword)
        logger.info(f"Found {len(companies)} companies for keyword '{keyword}'")
        return {
            "companies": companies,
            "total": len(companies)
        }
    except Exception as e:
        logger.error(f"Failed to search companies with keyword '{keyword}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{corp_code}", response_model=Company)
async def get_company(
    corp_code: str,
    dart_service: DARTService = Depends(get_dart_service)
):
    """특정 회사 정보 조회"""
    try:
        logger.info(f"Fetching company info for corp_code: {corp_code}")
        company = dart_service.get_company_by_code(corp_code)
        logger.info(f"Successfully fetched company: {company.get('corp_name')}")
        return company
    except Exception as e:
        logger.error(f"Failed to fetch company with corp_code {corp_code}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=404, detail=str(e))
