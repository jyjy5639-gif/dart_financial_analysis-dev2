"""
문서 기반 재무정보 추출 서비스
상장/비상장 구분 없이 공시문서에서 재무정보를 추출합니다.
"""
import os
import tempfile
from typing import Dict, List, Optional
from backend.repositories.dart_repository import DARTRepository
from backend.core.llm.upstage import UpstageProvider
from backend.core.exceptions import DARTAPIException, LLMException
from backend.core.logger import get_backend_logger

logger = get_backend_logger("document_financial_service")


class DocumentFinancialService:
    """문서 기반 재무정보 추출 서비스 (상장/비상장 통합)"""

    def __init__(self, dart_repo: DARTRepository, upstage_provider: Optional[UpstageProvider] = None):
        self.dart_repo = dart_repo
        self.upstage = upstage_provider

    async def extract_financial_from_document(
        self,
        rcept_no: str,
        corp_code: str,
        corp_name: str,
        report_nm: str,
        is_listed: bool = True
    ) -> Dict:
        """공시문서에서 재무정보 추출

        Args:
            rcept_no: 접수번호
            corp_code: 기업 고유번호
            corp_name: 기업명
            report_nm: 보고서명
            is_listed: 상장 여부

        Returns:
            추출된 재무정보 및 메타데이터
        """
        try:
            logger.info(f"Extracting financial data from document: {report_nm} ({rcept_no})")

            # 1. PDF 문서 다운로드
            temp_dir = tempfile.gettempdir()
            pdf_path = os.path.join(temp_dir, f"{corp_code}_{rcept_no}.pdf")

            logger.info(f"Downloading PDF document to {pdf_path}")
            self.dart_repo.download_document_pdf(rcept_no, pdf_path)

            try:
                # 2. Upstage Document Parse API로 PDF 파싱
                if not self.upstage:
                    return {
                        'success': False,
                        'error': 'Upstage API 키가 설정되지 않았습니다. PDF 파싱을 위해 Upstage API 키가 필요합니다.',
                        'rcept_no': rcept_no,
                        'report_nm': report_nm
                    }

                logger.info("Parsing PDF document with Upstage Document Parse API")
                parsed_data = await self.upstage.parse_document(pdf_path)

                # 3. 파싱된 데이터에서 재무제표 추출
                logger.info("Extracting financial data from parsed document")
                financial_data = await self.upstage.extract_financial_from_parsed_doc(
                    parsed_data,
                    corp_name,
                    report_nm
                )

                # 4. 재무제표 구조 분석 (연결/별도 구분)
                fs_structure = {
                    'has_consolidated': '연결' in report_nm,
                    'has_separate': '별도' in report_nm,
                    'default_type': 'CFS' if '연결' in report_nm else ('OFS' if '별도' in report_nm else 'N/A')
                }

                # 6. 표준 형식으로 변환
                result = self._convert_to_standard_format(
                    financial_data,
                    rcept_no,
                    corp_code,
                    corp_name,
                    report_nm,
                    fs_structure
                )

                logger.info(f"Successfully extracted financial data: {len(result['items'])} items")
                return {
                    'success': True,
                    'rcept_no': rcept_no,
                    'corp_code': corp_code,
                    'corp_name': corp_name,
                    'report_nm': report_nm,
                    'is_listed': is_listed,
                    'fs_structure': fs_structure,
                    'items': result['items'],
                    'ratios': result['ratios']
                }

            finally:
                # 5. 임시 PDF 파일 삭제
                if os.path.exists(pdf_path):
                    try:
                        os.remove(pdf_path)
                        logger.info(f"Cleaned up temporary PDF file: {pdf_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete temporary PDF file: {e}")

        except (DARTAPIException, LLMException) as e:
            logger.error(f"Financial extraction failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'rcept_no': rcept_no,
                'report_nm': report_nm
            }
        except Exception as e:
            logger.error(f"Unexpected error during financial extraction: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'재무정보 추출 실패: {str(e)}',
                'rcept_no': rcept_no,
                'report_nm': report_nm
            }

    def _convert_to_standard_format(
        self,
        financial_data: Dict,
        rcept_no: str,
        corp_code: str,
        corp_name: str,
        report_nm: str,
        fs_structure: Dict
    ) -> Dict:
        """표준 형식으로 변환"""
        from backend.services.dart_service import DARTService

        items = financial_data.get('items', [])

        # account_nm to account_id 매핑
        account_mapping = {
            '자산총계': 'ifrs-full_Assets',
            '부채총계': 'ifrs-full_Liabilities',
            '자본총계': 'ifrs-full_Equity',
            '매출액': 'ifrs-full_Revenue',
            '영업이익': 'dart_OperatingIncomeLoss',
            '당기순이익': 'ifrs-full_ProfitLoss',
        }

        # 연도 추출
        import re
        year_match = re.search(r'(\d{4})', report_nm)
        bsns_year = year_match.group(1) if year_match else "2023"

        # 날짜 계산
        current_year = int(bsns_year)
        thstrm_dt = f"{current_year}1231"
        frmtrm_dt = f"{current_year - 1}1231"
        bfefrmtrm_dt = f"{current_year - 2}1231"

        result_items = []
        for item in items:
            account_nm = item.get('account_nm', '')
            account_id = account_mapping.get(account_nm, '')

            standard_item = {
                'rcept_no': rcept_no,
                'reprt_code': '11011',
                'bsns_year': bsns_year,
                'corp_code': corp_code,
                'sj_div': 'BS' if account_nm in ['자산총계', '부채총계', '자본총계'] else 'IS',
                'sj_nm': '재무상태표' if account_nm in ['자산총계', '부채총계', '자본총계'] else '손익계산서',
                'account_id': account_id,
                'account_nm': account_nm,
                'account_detail': '-',
                'thstrm_nm': f"{bsns_year}년",
                'thstrm_dt': thstrm_dt,
                'thstrm_amount': str(item.get('thstrm_amount', '0')),
                'thstrm_add_amount': '0',
                'frmtrm_nm': f"{current_year - 1}년",
                'frmtrm_dt': frmtrm_dt,
                'frmtrm_amount': str(item.get('frmtrm_amount', '0')),
                'frmtrm_q_amount': '0',
                'frmtrm_add_amount': '0',
                'bfefrmtrm_nm': f"{current_year - 2}년",
                'bfefrmtrm_dt': bfefrmtrm_dt,
                'bfefrmtrm_amount': str(item.get('bfefrmtrm_amount', '0')),
                'ord': len(result_items) + 1,
                'currency': 'KRW',
            }

            result_items.append(standard_item)

        # 재무비율 계산
        ratios = self._calc_ratios(result_items)

        return {
            'items': result_items,
            'ratios': ratios
        }

    def _calc_ratios(self, data: List[Dict]) -> Dict[str, Dict[str, float]]:
        """재무비율 계산"""
        from backend.utils.formatters import safe_float

        # 계정별 금액 추출
        accts = {}
        for item in data:
            base_name = item.get('account_nm', '')
            accts[base_name] = {
                'thstrm': safe_float(item.get('thstrm_amount')),
                'frmtrm': safe_float(item.get('frmtrm_amount')),
                'bfefrmtrm': safe_float(item.get('bfefrmtrm_amount'))
            }

        def ratio(numerator: str, denominator: str, percentage: bool = True) -> Dict[str, float]:
            """비율 계산 헬퍼"""
            result = {}
            for period in ['thstrm', 'frmtrm', 'bfefrmtrm']:
                num = accts.get(numerator, {}).get(period, 0)
                den = accts.get(denominator, {}).get(period, 1)

                if den != 0:
                    value = (num / den) * (100 if percentage else 1)
                    result[period] = round(value, 2)
                else:
                    result[period] = 0.0

            return result

        return {
            '영업이익률': ratio('영업이익', '매출액', True),
            '순이익률': ratio('당기순이익', '매출액', True),
            'ROE': ratio('당기순이익', '자본총계', True),
            'ROA': ratio('당기순이익', '자산총계', True),
            '부채비율': ratio('부채총계', '자본총계', True),
            '자기자본비율': ratio('자본총계', '자산총계', True),
        }
