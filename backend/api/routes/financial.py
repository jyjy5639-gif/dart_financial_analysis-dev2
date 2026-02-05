from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime
from backend.services.dart_service import DARTService
from backend.services.financial_service import FinancialService
from backend.services.stock_service import StockService
from backend.services.excel_service import ExcelService
from backend.services.document_financial_service import DocumentFinancialService
from backend.api.dependencies import get_dart_service, get_financial_service, get_stock_service
from backend.core.logger import get_backend_logger
from backend.core.config import settings
from backend.core.llm.upstage import UpstageProvider
from pydantic import BaseModel

logger = get_backend_logger("financial")
router = APIRouter(prefix="/api/financial", tags=["financial"])

class ExcelDownloadRequest(BaseModel):
    """Excel download request"""
    companies: List[dict]


class MultipleCompaniesComparisonRequest(BaseModel):
    """Multiple companies comparison request"""
    corp_codes: List[str]
    bsns_year: str
    fs_div: str = "CFS"


@router.get("/{corp_code}")
async def get_financial_data(
    corp_code: str,
    bsns_year: str = Query(..., description="business year"),
    fs_div: str = Query("CFS", description="financial statement type"),
    dart_service: DARTService = Depends(get_dart_service)
):
    """Get financial data"""
    try:
        logger.info('Fetching financial data: corp_code={}, year={}, fs_div={}'.format(corp_code, bsns_year, fs_div))
        result = await dart_service.get_financial_data(corp_code, bsns_year, fs_div)

        if not result['items']:
            logger.warning('No financial data found: corp_code={}, year={}'.format(corp_code, bsns_year))
        else:
            logger.info('Successfully fetched {} financial items'.format(len(result['items'])))

        return {
            "financial_data": result['items'],
            "ratios": result['ratios'],
            "is_listed": result.get('is_listed', True),
            "source": result.get('source'),
            "error": result.get('error'),
            "message": result.get('error') or ("No data available" if not result['items'] else None)
        }
    except Exception as e:
        logger.error('Failed to fetch financial data: {}'.format(str(e)), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{corp_code}/stock-info")
async def get_stock_info(
    corp_code: str,
    stock_code: str = Query(...),
    corp_name: str = Query(None),
    bsns_year: Optional[int] = Query(None, description="business year for year-end indicators"),
    stock_service: StockService = Depends(get_stock_service)
):
    """Get stock information"""
    try:
        logger.info('Fetching stock info: stock_code={}, corp_name={}, bsns_year={}'.format(stock_code, corp_name, bsns_year))
        stock_info = stock_service.get_stock_info(stock_code, corp_name, bsns_year)
        logger.info('Successfully fetched stock info for {}'.format(stock_code))
        return stock_info
    except Exception as e:
        logger.error('Failed to fetch stock info: {}'.format(str(e)), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class CalcPerPbrRequest(BaseModel):
    """PER/PBR calculation request"""
    stock_code: str
    corp_name: Optional[str] = None
    financial_items: List[dict]


@router.post("/{corp_code}/calc-per-pbr")
async def calc_per_pbr(
    corp_code: str,
    request: CalcPerPbrRequest,
    stock_service: StockService = Depends(get_stock_service)
):
    """Calculate PER/PBR using financial data and stock info"""
    try:
        logger.info('Calculating PER/PBR: corp_code={}, stock_code={}'.format(corp_code, request.stock_code))

        # Get stock info
        stock_info = stock_service.get_stock_info(request.stock_code, request.corp_name)

        # Prepare financial data format
        financial_data = {'items': request.financial_items}

        # Calculate PER/PBR
        result = stock_service.calc_per_pbr(financial_data, stock_info)

        logger.info('PER/PBR calculation complete: PER={}, PBR={}'.format(
            result.get('PER', {}).get('thstrm'),
            result.get('PBR', {}).get('thstrm')
        ))

        return {
            'success': True,
            'per': result.get('PER'),
            'pbr': result.get('PBR'),
            'note': result.get('note'),
            'stock_price': stock_info.get('price'),
            'shares': stock_info.get('shares')
        }
    except Exception as e:
        logger.error('Failed to calculate PER/PBR: {}'.format(str(e)), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{corp_code}/disclosures")
async def get_disclosures(
    corp_code: str,
    bsns_year: str = Query(...),
    dart_service: DARTService = Depends(get_dart_service)
):
    """Get disclosure list"""
    try:
        logger.info('Fetching disclosures: corp_code={}, year={}'.format(corp_code, bsns_year))
        result = dart_service.get_disclosure_list(corp_code, bsns_year)
        logger.info('Successfully fetched {} disclosures'.format(result['total']))
        return result
    except Exception as e:
        logger.error('Failed to fetch disclosures: {}'.format(str(e)), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{corp_code}/financial-documents")
async def get_financial_documents(
    corp_code: str,
    start_year: Optional[str] = Query(None, description="start year"),
    end_year: Optional[str] = Query(None, description="end year"),
    dart_service: DARTService = Depends(get_dart_service)
):
    """Get financial documents list"""
    try:
        logger.info('Fetching financial documents: corp_code={}, start_year={}, end_year={}'.format(corp_code, start_year, end_year))

        # Get company information
        company = dart_service.get_company_by_code(corp_code)

        # Get financial documents list
        documents = dart_service.dart_repo.get_financial_documents(corp_code, start_year, end_year)

        logger.info('Successfully fetched {} financial documents'.format(len(documents)))
        return {
            'corp_code': corp_code,
            'corp_name': company['corp_name'],
            'stock_code': company['stock_code'],
            'is_listed': company['stock_code'] != 'N/A',
            'documents': documents,
            'total': len(documents)
        }
    except Exception as e:
        logger.error('Failed to fetch financial documents: {}'.format(str(e)), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{corp_code}/extract-from-document")
async def extract_financial_from_document(
    corp_code: str,
    rcept_no: str = Query(..., description="receipt number"),
    report_nm: str = Query(..., description="report name"),
    dart_service: DARTService = Depends(get_dart_service)
):
    """Extract financial information from disclosure document"""
    try:
        logger.info('Extracting financial data from document: rcept_no={}'.format(rcept_no))

        # Get company information
        company = dart_service.get_company_by_code(corp_code)
        is_listed = company['stock_code'] != 'N/A'

        # Create DocumentFinancialService
        upstage_provider = None
        if settings.upstage_api_key:
            upstage_provider = UpstageProvider(settings.upstage_api_key)

        doc_service = DocumentFinancialService(dart_service.dart_repo, upstage_provider)

        # Extract financial information
        result = await doc_service.extract_financial_from_document(
            rcept_no=rcept_no,
            corp_code=corp_code,
            corp_name=company['corp_name'],
            report_nm=report_nm,
            is_listed=is_listed
        )

        if not result.get('success'):
            logger.warning('Failed to extract financial data: {}'.format(result.get('error')))
            return {
                'success': False,
                'error': result.get('error'),
                'message': result.get('error')
            }

        logger.info('Successfully extracted {} financial items'.format(len(result.get('items', []))))
        return {
            'success': True,
            'financial_data': result.get('items', []),
            'ratios': result.get('ratios', {}),
            'is_listed': result.get('is_listed'),
            'fs_structure': result.get('fs_structure'),
            'corp_name': company['corp_name'],
            'stock_code': company['stock_code'],
            'report_nm': report_nm,
            'rcept_no': rcept_no
        }
    except Exception as e:
        logger.error('Failed to extract financial data from document: {}'.format(str(e)), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/comparison/multiple")
async def get_multiple_companies_comparison(
    request: MultipleCompaniesComparisonRequest,
    dart_service: DARTService = Depends(get_dart_service),
    financial_service: FinancialService = Depends(get_financial_service)
):
    """
    Get financial data for multiple companies for side-by-side comparison.
    
    Request:
    {
        "corp_codes": ["00005930", "00066570"],
        "bsns_year": "2024",
        "fs_div": "CFS"
    }
    
    Response:
    {
        "success": true,
        "comparison_data": {
            "2024": [
                {
                    "corp_code": "00005930",
                    "corp_name": "Samsung Electronics",
                    "financial_data": [...],
                    "ratios": {...}
                },
                {
                    "corp_code": "00066570",
                    "corp_name": "LG Electronics",
                    "financial_data": [...],
                    "ratios": {...}
                }
            ],
            "2023": [...],
            "2022": [...]
        }
    }
    """
    try:
        logger.info('Fetching comparison data for {} companies'.format(len(request.corp_codes)))
        
        if len(request.corp_codes) < 2:
            raise HTTPException(status_code=400, detail='At least 2 companies required for comparison')
        
        # Step 1: Get company information
        company_info = {}
        companies_financial_data = {}
        
        for corp_code in request.corp_codes:
            try:
                company = dart_service.get_company_by_code(corp_code)
                company_info[corp_code] = company
                
                # Get financial data for this company
                years = [
                    str(int(request.bsns_year)),
                    str(int(request.bsns_year) - 1),
                    str(int(request.bsns_year) - 2)
                ]
                
                all_financial_data = []
                for year in years:
                    try:
                        result = await dart_service.get_financial_data(corp_code, year, request.fs_div)
                        if result and result.get('items'):
                            all_financial_data.extend(result['items'])
                    except Exception as year_error:
                        logger.warning('Failed to fetch data for corp_code={}, year={}: {}'.format(corp_code, year, str(year_error)))
                
                companies_financial_data[corp_code] = all_financial_data
                logger.info('Successfully fetched {} items for corp_code={}'.format(len(all_financial_data), corp_code))
                
            except Exception as company_error:
                logger.error('Failed to process corp_code={}: {}'.format(corp_code, str(company_error)))
                raise HTTPException(status_code=500, detail='Failed to process corp_code={}: {}'.format(corp_code, str(company_error)))
        
        # Step 2: Prepare comparison data
        companies_comparison_data = financial_service.prepare_comparison_data(companies_financial_data)
        
        # Step 3: Format data by year
        comparison_data = financial_service.format_comparison_by_year(
            companies_comparison_data,
            company_info
        )
        
        logger.info('Successfully prepared comparison data for {} companies'.format(len(request.corp_codes)))
        
        return {
            'success': True,
            'comparison_data': comparison_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error('Failed to fetch comparison data: {}'.format(str(e)), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download-excel")
async def download_financial_excel(request: ExcelDownloadRequest):
    """Download financial information as Excel file"""
    try:
        logger.info('Excel download requested for {} companies'.format(len(request.companies)))
        
        if not request.companies:
            raise HTTPException(status_code=400, detail='No company data')
        
        financial_data = []
        
        for company in request.companies:
            corp_name = company.get('corp_name', 'Unknown')
            stock_code = company.get('stock_code', 'N/A')
            financial_items = company.get('financial_data', [])
            ratios = company.get('ratios', {})
            
            logger.info('Processing company: {}, items={}'.format(corp_name, len(financial_items)))
            
            financial_statements = {
                'balance_sheet': {},
                'income_statement': {},
                'cash_flow': {},
                'ratios': ratios
            }
            
            for item in financial_items:
                account_nm = item.get('display_name', item.get('account_nm', ''))
                sj_div = item.get('sj_div', '')
                
                year_data = {}
                
                if item.get('thstrm_dt'):
                    year = item['thstrm_dt'][:4] if len(item['thstrm_dt']) >= 4 else None
                    if year:
                        year_data[year] = item.get('thstrm_amount', 0)
                
                if item.get('frmtrm_dt'):
                    year = item['frmtrm_dt'][:4] if len(item['frmtrm_dt']) >= 4 else None
                    if year:
                        year_data[year] = item.get('frmtrm_amount', 0)
                
                if item.get('bfefrmtrm_dt'):
                    year = item['bfefrmtrm_dt'][:4] if len(item['bfefrmtrm_dt']) >= 4 else None
                    if year:
                        year_data[year] = item.get('bfefrmtrm_amount', 0)
                
                if sj_div == 'BS':
                    financial_statements['balance_sheet'][account_nm] = year_data
                elif sj_div == 'IS':
                    financial_statements['income_statement'][account_nm] = year_data
                elif sj_div == 'CF':
                    financial_statements['cash_flow'][account_nm] = year_data
            
            financial_data.append({
                'company_name': corp_name,
                'stock_code': stock_code,
                'financial_statements': financial_statements
            })
        
        logger.info('Creating Excel file...')
        excel_file = ExcelService.create_financial_excel(financial_data)
        
        if len(financial_data) == 1:
            filename = 'financial_statements_{}_{}.xlsx'.format(financial_data[0]['company_name'], datetime.now().strftime('%Y%m%d'))
        else:
            filename = 'financial_statements_comparison_{}.xlsx'.format(datetime.now().strftime('%Y%m%d'))
        
        logger.info('Excel file created successfully: {}'.format(filename))
        
        from urllib.parse import quote
        encoded_filename = quote(filename)
        
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename*=UTF-8''{}".format(encoded_filename),
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error('Excel download failed: {}'.format(str(e)), exc_info=True)
        import traceback
        error_detail = '{}\n\nTraceback:\n{}'.format(str(e), traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)