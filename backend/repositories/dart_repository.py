import requests
import xml.etree.ElementTree as ET
import zipfile
import io
from typing import List, Dict, Optional
from backend.core.exceptions import DARTAPIException
from backend.core.config import settings
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class DARTRepository:
    """DART API 데이터 액세스 레이어"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.dart_api_key
        self.base_url = settings.dart_base_url
    
    def download_corp_codes(self) -> List[Dict]:
        """회사 코드 다운로드"""
        try:
            response = requests.get(
                f"{self.base_url}/corpCode.xml",
                params={'crtfc_key': self.api_key.strip()},
                verify=False,
                timeout=30
            )
            response.raise_for_status()
            
            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                with zf.open('CORPCODE.xml') as f:
                    root = ET.parse(f).getroot()
                    corp_list = []
                    
                    for item in root.findall('.//list'):
                        corp_code = item.findtext('corp_code')
                        corp_name = item.findtext('corp_name')
                        stock_code = item.findtext('stock_code', '').strip() or 'N/A'
                        
                        if corp_code and corp_name:
                            corp_list.append({
                                'corp_code': corp_code,
                                'corp_name': corp_name,
                                'stock_code': stock_code
                            })
                    
                    return corp_list
                    
        except Exception as e:
            raise DARTAPIException(f"회사 코드 다운로드 실패: {str(e)}")
    
    def get_financial_data(
        self,
        corp_code: str,
        bsns_year: str,
        fs_div: str = 'CFS'
    ) -> List[Dict]:
        """재무정보 조회
        
        Args:
            corp_code: 기업 고유번호
            bsns_year: 사업연도 (YYYY)
            fs_div: 재무제표 구분 (CFS: 연결, OFS: 별도)
            
        Returns:
            재무 데이터 리스트
        """
        try:
            url = f"{self.base_url}/fnlttMultiAcnt.json"
            params = {
                'crtfc_key': self.api_key,
                'corp_code': corp_code,
                'bsns_year': bsns_year,
                'reprt_code': '11011',  # 사업보고서
            }
            
            response = requests.get(url, params=params, verify=False, timeout=30)
            data = response.json()
            
            if data.get('status') == '000':
                return [i for i in data.get('list', []) if i.get('fs_div') == fs_div]
            else:
                return []
                
        except Exception as e:
            raise DARTAPIException(f"재무정보 조회 실패: {str(e)}")
    
    def get_disclosure_list(
        self,
        corp_code: str,
        bsns_year: str
    ) -> List[Dict]:
        """공시 목록 조회

        Args:
            corp_code: 기업 고유번호
            bsns_year: 사업연도 (YYYY)

        Returns:
            공시 목록
        """
        try:
            url = f"{self.base_url}/list.json"

            params = {
                'crtfc_key': self.api_key,
                'corp_code': corp_code,
                'bgn_de': f"{bsns_year}0101",
                'end_de': f"{bsns_year}1231",
                'page_count': '100'
            }

            response = requests.get(url, params=params, verify=False, timeout=30)
            data = response.json()

            if data.get('status') == '000':
                return data.get('list', [])
            else:
                return []

        except Exception as e:
            raise DARTAPIException(f"공시 조회 실패: {str(e)}")

    def search_report_documents(
        self,
        corp_code: str,
        bsns_year: str,
        report_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """사업보고서/감사보고서 검색

        Args:
            corp_code: 기업 고유번호
            bsns_year: 사업연도 (YYYY)
            report_types: 보고서 유형 리스트 (기본값: 사업보고서, 감사보고서)

        Returns:
            검색된 보고서 목록
        """
        if report_types is None:
            report_types = ['사업보고서', '감사보고서']

        try:
            disclosures = self.get_disclosure_list(corp_code, bsns_year)

            # 사업보고서 또는 감사보고서만 필터링
            reports = []
            for doc in disclosures:
                report_nm = doc.get('report_nm', '')
                # 정정, 첨부정정 제외
                if any(rt in report_nm for rt in report_types) and '정정' not in report_nm:
                    reports.append(doc)

            return reports

        except Exception as e:
            raise DARTAPIException(f"보고서 검색 실패: {str(e)}")

    def get_financial_documents(
        self,
        corp_code: str,
        start_year: Optional[str] = None,
        end_year: Optional[str] = None
    ) -> List[Dict]:
        """재무정보가 포함된 공시 문서 목록 조회

        Args:
            corp_code: 기업 고유번호
            start_year: 시작 연도 (선택, 기본값: 현재년도-3)
            end_year: 종료 연도 (선택, 기본값: 현재년도)

        Returns:
            재무정보가 포함된 문서 목록
        """
        try:
            from datetime import datetime

            if not end_year:
                end_year = str(datetime.now().year)
            if not start_year:
                start_year = str(int(end_year) - 3)

            url = f"{self.base_url}/list.json"

            params = {
                'crtfc_key': self.api_key,
                'corp_code': corp_code,
                'bgn_de': f"{start_year}0101",
                'end_de': f"{end_year}1231",
                'page_count': '100'
            }

            response = requests.get(url, params=params, verify=False, timeout=30)
            data = response.json()

            if data.get('status') != '000':
                return []

            disclosures = data.get('list', [])

            # 재무정보가 있는 문서만 필터링
            financial_keywords = [
                '사업보고서', '반기보고서', '분기보고서',
                '감사보고서', '검토보고서'
            ]

            exclude_keywords = ['정정', '취소', '철회', '연장', '첨부정정']

            financial_docs = []
            for doc in disclosures:
                report_nm = doc.get('report_nm', '')

                # 재무정보 포함 문서만 선택
                if any(kw in report_nm for kw in financial_keywords):
                    # 제외 키워드 체크
                    if not any(ex in report_nm for ex in exclude_keywords):
                        financial_docs.append({
                            'rcept_no': doc.get('rcept_no'),
                            'corp_code': doc.get('corp_code'),
                            'corp_name': doc.get('corp_name'),
                            'report_nm': report_nm,
                            'rcept_dt': doc.get('rcept_dt'),
                            'flr_nm': doc.get('flr_nm'),
                            'rm': doc.get('rm', '')
                        })

            # 접수일자 기준 내림차순 정렬
            financial_docs.sort(key=lambda x: x['rcept_dt'], reverse=True)

            return financial_docs

        except Exception as e:
            raise DARTAPIException(f"재무문서 목록 조회 실패: {str(e)}")

    def download_document(
        self,
        rcept_no: str,
        save_path: str
    ) -> str:
        """공시문서 다운로드 (HTML/XML)

        Args:
            rcept_no: 접수번호
            save_path: 저장 경로

        Returns:
            저장된 파일 경로
        """
        try:
            url = f"{self.base_url}/document.xml"
            params = {
                'crtfc_key': self.api_key,
                'rcept_no': rcept_no
            }

            response = requests.get(url, params=params, verify=False, timeout=60)
            response.raise_for_status()

            # 파일로 저장
            import os
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            with open(save_path, 'wb') as f:
                f.write(response.content)

            return save_path

        except Exception as e:
            raise DARTAPIException(f"문서 다운로드 실패: {str(e)}")

    def download_document_pdf(
        self,
        rcept_no: str,
        save_path: str
    ) -> str:
        """공시문서 PDF 다운로드

        Args:
            rcept_no: 접수번호
            save_path: 저장 경로

        Returns:
            저장된 PDF 파일 경로
        """
        try:
            # DART PDF 다운로드 URL
            url = "https://dart.fss.or.kr/pdf/download/main.do"
            params = {
                'rcp_no': rcept_no
            }

            response = requests.get(url, params=params, verify=False, timeout=120)
            response.raise_for_status()

            # PDF인지 확인
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' not in content_type.lower() and not save_path.endswith('.pdf'):
                raise DARTAPIException(f"PDF 다운로드 실패: 응답이 PDF가 아닙니다 (Content-Type: {content_type})")

            # 파일로 저장
            import os
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            with open(save_path, 'wb') as f:
                f.write(response.content)

            return save_path

        except Exception as e:
            raise DARTAPIException(f"PDF 다운로드 실패: {str(e)}")


if __name__ == "__main__":
    """
    PDF 다운로드 테스트

    실행 방법:
    1. DART_API_KEY 환경변수 설정 또는 아래 api_key 직접 입력
    2. 터미널에서 실행: python -m backend.repositories.dart_repository
    3. 또는 VSCode에서 직접 Run
    """
    import os

    # DART API 키 (환경변수 또는 직접 입력)
    api_key = os.getenv('DART_API_KEY', '205a6f152ccca428c2b411daf87b77e5b2eea014')

    # 테스트할 공시 접수번호 (예시)
    # 삼성전자 2023 사업보고서: 20240318000267
    # SK하이닉스 2023 사업보고서: 20240329000285
    test_rcept_no = "20250407003780"  # 삼성전자 2023 사업보고서

    # PDF 저장 경로 (프로젝트 루트의 downloads 폴더)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    downloads_dir = os.path.join(project_root, "downloads")
    os.makedirs(downloads_dir, exist_ok=True)

    pdf_filename = f"test_document_{test_rcept_no}.pdf"
    pdf_path = os.path.join(downloads_dir, pdf_filename)

    print("=" * 60)
    print("DART PDF 다운로드 테스트")
    print("=" * 60)
    print(f"접수번호: {test_rcept_no}")
    print(f"저장 경로: {pdf_path}")
    print("-" * 60)

    try:
        # DARTRepository 인스턴스 생성
        print("PDF 다운로드 중...")
        try:
            # DART PDF 다운로드 URL
            url = "https://dart.fss.or.kr/pdf/download/main.do"
            params = {
                'rcp_no': test_rcept_no
            }

            response = requests.get(url, params=params, verify=False, timeout=120)
            response.raise_for_status()

            # PDF인지 확인
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' not in content_type.lower() and not pdf_path.endswith('.pdf'):
                raise DARTAPIException(f"PDF 다운로드 실패: 응답이 PDF가 아닙니다 (Content-Type: {content_type})")

            # 파일로 저장
            import os
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

            with open(pdf_path, 'wb') as f:
                f.write(response.content)

        except Exception as e:
            raise DARTAPIException(f"PDF 다운로드 실패: {str(e)}")
        
        
        # 파일 크기 확인
        file_size = os.path.getsize(pdf_path)
        file_size_mb = file_size / (1024 * 1024)

        print(f"✓ 다운로드 완료!")
        print(f"  - 파일 크기: {file_size_mb:.2f} MB ({file_size:,} bytes)")
        print(f"  - 저장 위치: {pdf_path}")
        print("-" * 60)
        print(f"파일 탐색기에서 확인: {downloads_dir}")
        print("=" * 60)

    except DARTAPIException as e:
        print(f"✗ DART API 오류: {e}")
        print("\n확인 사항:")
        print("  1. DART API 키가 올바르게 설정되었는지 확인")
        print("  2. 접수번호가 유효한지 확인")
        print("  3. 인터넷 연결 확인")
    except Exception as e:
        print(f"✗ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
