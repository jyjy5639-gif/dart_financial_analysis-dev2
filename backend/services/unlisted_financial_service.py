import os
import tempfile
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from backend.repositories.dart_repository import DARTRepository
from backend.core.llm.upstage import UpstageProvider
from backend.core.exceptions import DARTAPIException, LLMException
from backend.core.config import settings
from backend.core.logger import get_backend_logger

logger = get_backend_logger("unlisted_financial_service")


class UnlistedFinancialService:
    """비상장 기업 재무정보 파싱 서비스"""

    def __init__(self, dart_repo: DARTRepository, upstage_provider: UpstageProvider):
        self.dart_repo = dart_repo
        self.upstage = upstage_provider

    async def get_unlisted_financial_data(
        self,
        corp_code: str,
        corp_name: str,
        bsns_year: str
    ) -> List[Dict]:
        """비상장 기업의 재무정보 조회 (사업보고서/감사보고서에서 추출)

        Args:
            corp_code: 기업 고유번호
            corp_name: 기업명
            bsns_year: 사업연도

        Returns:
            재무 데이터 리스트 (상장 기업 형식과 동일)
        """
        try:
            logger.info(f"Getting unlisted financial data for {corp_name} ({bsns_year})")

            # 1. 사업보고서/감사보고서 검색
            reports = self.dart_repo.search_report_documents(corp_code, bsns_year)

            if not reports:
                logger.warning(f"No reports found for {corp_name} ({bsns_year})")
                return []

            # 2. 가장 최신 보고서 선택 (감사보고서 우선)
            audit_reports = [r for r in reports if '감사보고서' in r.get('report_nm', '')]
            business_reports = [r for r in reports if '사업보고서' in r.get('report_nm', '')]

            selected_report = None
            if audit_reports:
                selected_report = audit_reports[0]
                logger.info(f"Selected audit report: {selected_report.get('report_nm')}")
            elif business_reports:
                selected_report = business_reports[0]
                logger.info(f"Selected business report: {selected_report.get('report_nm')}")
            else:
                raise DARTAPIException("사업보고서 또는 감사보고서를 찾을 수 없습니다.")

            # 3. 문서 다운로드
            rcept_no = selected_report.get('rcept_no')
            temp_dir = tempfile.gettempdir()
            html_path = os.path.join(temp_dir, f"{corp_code}_{bsns_year}_{rcept_no}.html")

            logger.info(f"Downloading document to {html_path}")
            self.dart_repo.download_document(rcept_no, html_path)

            try:
                # 4. HTML 파싱하여 재무제표 테이블 추출
                logger.info("Parsing HTML document for financial tables")
                # DART 문서는 보통 EUC-KR 또는 UTF-8 인코딩을 사용하므로 자동 감지
                try:
                    with open(html_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                except UnicodeDecodeError:
                    logger.info("UTF-8 decoding failed, trying EUC-KR encoding")
                    with open(html_path, 'r', encoding='euc-kr') as f:
                        html_content = f.read()

                financial_tables = self._extract_financial_tables(html_content)

                if not financial_tables:
                    logger.warning("No financial tables found in document")
                    raise DARTAPIException("문서에서 재무제표를 찾을 수 없습니다.")

                # 5. LLM으로 재무정보 추출
                logger.info("Extracting financial data with LLM")
                financial_data = await self.upstage.extract_financial_from_html_tables(
                    financial_tables,
                    corp_name,
                    bsns_year
                )

                # 6. 상장 기업 형식으로 변환
                result = self._convert_to_standard_format(financial_data, bsns_year)

                logger.info(f"Successfully extracted {len(result)} financial items")
                return result

            finally:
                # 7. 임시 파일 삭제
                if os.path.exists(html_path):
                    try:
                        os.remove(html_path)
                        logger.info(f"Cleaned up temporary file: {html_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete temporary file: {e}")

        except (DARTAPIException, LLMException):
            raise
        except Exception as e:
            logger.error(f"Unlisted financial data extraction failed: {str(e)}", exc_info=True)
            raise DARTAPIException(f"비상장 기업 재무정보 조회 실패: {str(e)}")

    def _extract_financial_tables(self, html_content: str) -> str:
        """HTML에서 재무제표 테이블 추출

        Args:
            html_content: HTML 문서 내용

        Returns:
            추출된 재무제표 테이블 텍스트
        """
        try:
            soup = BeautifulSoup(html_content, 'lxml')

            # 재무제표 관련 키워드
            financial_keywords = [
                '재무상태표', '재무 상태표', '대차대조표',
                '손익계산서', '손익 계산서', '포괄손익계산서',
                '자산총계', '부채총계', '자본총계', '매출액'
            ]

            # 모든 테이블 찾기
            tables = soup.find_all('table')
            logger.info(f"Found {len(tables)} tables in document")

            financial_tables = []

            for idx, table in enumerate(tables):
                table_text = table.get_text(separator=' ', strip=True)

                # 재무제표 관련 키워드가 있는 테이블만 선택
                if any(keyword in table_text for keyword in financial_keywords):
                    # 테이블을 텍스트로 변환 (구조 유지)
                    table_str = self._table_to_text(table)
                    financial_tables.append(table_str)
                    logger.info(f"Table {idx} identified as financial table")

            if not financial_tables:
                logger.warning("No financial tables found based on keywords")
                return ""

            # 처음 10개 테이블만 사용 (너무 많으면 LLM 토큰 제한)
            combined_tables = '\n\n---테이블 구분---\n\n'.join(financial_tables[:10])
            logger.info(f"Extracted {len(financial_tables[:10])} financial tables, total length: {len(combined_tables)}")

            return combined_tables

        except Exception as e:
            logger.error(f"Failed to extract financial tables: {str(e)}", exc_info=True)
            return ""

    def _table_to_text(self, table) -> str:
        """HTML 테이블을 텍스트 형식으로 변환

        Args:
            table: BeautifulSoup table 객체

        Returns:
            텍스트 형식의 테이블
        """
        rows = []
        for tr in table.find_all('tr'):
            cells = []
            for td in tr.find_all(['td', 'th']):
                text = td.get_text(strip=True)
                cells.append(text)
            if cells:
                rows.append(' | '.join(cells))

        return '\n'.join(rows)

    def _convert_to_standard_format(
        self,
        financial_data: Dict,
        bsns_year: str
    ) -> List[Dict]:
        """LLM 추출 데이터를 상장 기업 형식으로 변환

        Args:
            financial_data: LLM이 추출한 재무 데이터
            bsns_year: 사업연도

        Returns:
            표준 형식의 재무 데이터 리스트
        """
        items = financial_data.get('items', [])
        result = []

        # account_nm to account_id 매핑
        account_mapping = {
            '자산총계': 'ifrs-full_Assets',
            '부채총계': 'ifrs-full_Liabilities',
            '자본총계': 'ifrs-full_Equity',
            '매출액': 'ifrs-full_Revenue',
            '영업이익': 'dart_OperatingIncomeLoss',
            '당기순이익': 'ifrs-full_ProfitLoss',
        }

        # 날짜 계산 (12월 31일 기준)
        current_year = int(bsns_year)
        thstrm_dt = f"{current_year}1231"
        frmtrm_dt = f"{current_year - 1}1231"
        bfefrmtrm_dt = f"{current_year - 2}1231"

        for item in items:
            account_nm = item.get('account_nm', '')
            account_id = account_mapping.get(account_nm, '')

            standard_item = {
                'rcept_no': '',
                'reprt_code': '11011',  # 사업보고서
                'bsns_year': bsns_year,
                'corp_code': '',
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
                'ord': len(result) + 1,
                'currency': 'KRW',
            }

            result.append(standard_item)

        return result
