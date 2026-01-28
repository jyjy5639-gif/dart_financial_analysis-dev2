from typing import Dict
import httpx
from .base import BaseLLMProvider
from ..exceptions import LLMException
from ..logger import get_backend_logger

logger = get_backend_logger("llm.upstage")


class UpstageProvider(BaseLLMProvider):
    """Upstage Solar LLM 제공자"""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://api.upstage.ai/v1/solar"
        self.document_parse_url = "https://api.upstage.ai/v1/document-ai/document-parse"
        self.model_name = "solar-pro2"
        logger.info(f"Upstage provider initialized with model: {self.model_name}")
    
    async def generate_briefing(
        self,
        corp_name: str,
        financial_data: Dict,
        style: str = "default"
    ) -> str:
        """Upstage Solar로 재무 브리핑 생성"""
        
        try:
            logger.info(f"Generating briefing for {corp_name} with style: {style}")
            prompt = self._build_prompt(corp_name, financial_data, style)
            logger.info(f"Prompt length: {len(prompt)} characters")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": "당신은 재무 분석 전문가입니다. 반드시 한글로만 답변하세요."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 4000,
                "reasoning_effort": "high"
            }
            
            logger.info("Sending request to Upstage API...")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
            
            if data.get("choices") and len(data["choices"]) > 0:
                briefing_text = data["choices"][0]["message"]["content"].strip()
                logger.info(f"Successfully generated briefing: {len(briefing_text)} characters")
                
                # 텍스트 유효성 검증
                if len(briefing_text) < 100:
                    logger.warning(f"Briefing text is too short: {len(briefing_text)} chars")
                    raise LLMException("생성된 브리핑이 너무 짧습니다. 다시 시도해주세요.")
                
                return briefing_text
            else:
                logger.error("Received empty response from Upstage API")
                raise LLMException("Upstage API로부터 응답을 받지 못했습니다.")
                
        except LLMException:
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Upstage HTTP error: {e.response.status_code} - {e.response.text}")
            
            if e.response.status_code == 429:
                raise LLMException("API 사용량 한도 초과. 잠시 후 다시 시도하세요.")
            elif e.response.status_code == 401 or e.response.status_code == 403:
                raise LLMException(
                    "유효하지 않은 API 키입니다.\n"
                    "발급: https://console.upstage.ai/"
                )
            else:
                raise LLMException(f"브리핑 생성 실패: HTTP {e.response.status_code}")
        except Exception as e:
            logger.error(f"Upstage API error: {str(e)}", exc_info=True)
            raise LLMException(f"브리핑 생성 실패: {str(e)}")
    
    def is_available(self) -> bool:
        """Upstage API 사용 가능 여부"""
        return bool(self.api_key)

    async def parse_document(self, file_path: str) -> Dict:
        """PDF 문서 파싱 (Document Parse API)

        Args:
            file_path: PDF 파일 경로

        Returns:
            파싱된 문서 데이터 (텍스트, 테이블 등)
        """
        try:
            logger.info(f"Parsing document: {file_path}")

            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }

            with open(file_path, 'rb') as f:
                files = {
                    'document': f
                }

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.document_parse_url,
                        headers=headers,
                        files=files,
                        timeout=120.0
                    )
                    response.raise_for_status()
                    data = response.json()

            logger.info(f"Document parsed successfully: {len(data.get('elements', []))} elements found")
            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"Document parse HTTP error: {e.response.status_code} - {e.response.text}")
            raise LLMException(f"문서 파싱 실패: HTTP {e.response.status_code}")
        except Exception as e:
            logger.error(f"Document parse error: {str(e)}", exc_info=True)
            raise LLMException(f"문서 파싱 실패: {str(e)}")

    async def extract_financial_from_parsed_doc(
        self,
        parsed_data: Dict,
        corp_name: str,
        report_nm: str
    ) -> Dict:
        """파싱된 문서에서 재무정보 추출 (LLM 사용)

        Args:
            parsed_data: Document Parse API 결과
            corp_name: 회사명
            report_nm: 보고서명 (연도 추출용)

        Returns:
            구조화된 재무 데이터
        """
        # 보고서명에서 연도 추출
        import re
        year_match = re.search(r'(\d{4})', report_nm)
        bsns_year = year_match.group(1) if year_match else "2023"
        try:
            logger.info(f"Extracting financial data for {corp_name} ({bsns_year})")

            # 파싱된 데이터에서 텍스트 추출
            elements = parsed_data.get('elements', [])

            # 재무제표 관련 페이지 필터링 (테이블이 있는 페이지)
            financial_text = []
            for element in elements:
                if element.get('category') == 'table':
                    # 테이블 데이터 추출
                    table_html = element.get('html', '')
                    financial_text.append(table_html)
                elif element.get('category') == 'paragraph':
                    text = element.get('text', '')
                    # 재무제표 관련 키워드가 있는 경우만
                    if any(keyword in text for keyword in ['재무상태표', '손익계산서', '포괄손익계산서', '자산총계', '부채총계', '매출액']):
                        financial_text.append(text)

            if not financial_text:
                raise LLMException("문서에서 재무제표를 찾을 수 없습니다.")

            # 재무정보 추출용 프롬프트
            combined_text = '\n\n'.join(financial_text[:50])  # 처음 50개 요소만 사용

            prompt = f"""
다음은 {corp_name}의 {bsns_year}년 사업보고서/감사보고서에서 추출한 재무제표 데이터입니다.

{combined_text}

위 데이터에서 다음 재무 항목을 추출하여 JSON 형식으로 반환해주세요:

1. 자산총계 (당기, 전기, 전전기)
2. 부채총계 (당기, 전기, 전전기)
3. 자본총계 (당기, 전기, 전전기)
4. 매출액 (당기, 전기, 전전기)
5. 영업이익 (당기, 전기, 전전기)
6. 당기순이익 (당기, 전기, 전전기)

응답 형식:
{{
  "items": [
    {{
      "account_nm": "자산총계",
      "thstrm_amount": "당기금액(숫자만)",
      "frmtrm_amount": "전기금액(숫자만)",
      "bfefrmtrm_amount": "전전기금액(숫자만)"
    }},
    ...
  ]
}}

금액은 원 단위 숫자로만 반환하고, 콤마나 단위는 제거해주세요.
데이터가 없는 경우 "0"으로 표시해주세요.
JSON 외의 다른 텍스트는 포함하지 마세요.
"""

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": "당신은 재무제표 분석 전문가입니다. 주어진 재무제표에서 정확한 숫자를 추출하여 JSON 형식으로 반환합니다."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 2000
            }

            logger.info("Sending request to Upstage API for financial extraction...")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()

            if data.get("choices") and len(data["choices"]) > 0:
                result_text = data["choices"][0]["message"]["content"].strip()
                logger.info(f"Financial extraction result: {result_text[:200]}...")

                # JSON 파싱
                import json
                import re

                # JSON 부분만 추출
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    financial_data = json.loads(json_match.group())
                    return financial_data
                else:
                    raise LLMException("재무정보 추출 결과를 파싱할 수 없습니다.")
            else:
                raise LLMException("재무정보 추출 실패")

        except LLMException:
            raise
        except Exception as e:
            logger.error(f"Financial extraction error: {str(e)}", exc_info=True)
            raise LLMException(f"재무정보 추출 실패: {str(e)}")

    async def extract_financial_from_html_tables(
        self,
        tables_text: str,
        corp_name: str,
        bsns_year: str
    ) -> Dict:
        """HTML 테이블에서 재무정보 추출 (LLM 사용)

        Args:
            tables_text: 추출된 재무제표 테이블 텍스트
            corp_name: 회사명
            bsns_year: 사업연도

        Returns:
            구조화된 재무 데이터
        """
        try:
            logger.info(f"Extracting financial data from HTML tables for {corp_name} ({bsns_year})")

            if not tables_text:
                raise LLMException("재무제표 테이블이 비어있습니다.")

            # 재무정보 추출용 프롬프트
            prompt = f"""
다음은 {corp_name}의 {bsns_year}년 사업보고서/감사보고서에서 추출한 재무제표 테이블입니다.

{tables_text[:15000]}

위 테이블에서 다음 재무 항목을 추출하여 JSON 형식으로 반환해주세요:

1. 자산총계 (당기, 전기, 전전기)
2. 부채총계 (당기, 전기, 전전기)
3. 자본총계 (당기, 전기, 전전기)
4. 매출액 (당기, 전기, 전전기)
5. 영업이익 (당기, 전기, 전전기)
6. 당기순이익 (당기, 전기, 전전기)

응답 형식:
{{
  "items": [
    {{
      "account_nm": "자산총계",
      "thstrm_amount": "당기금액(숫자만)",
      "frmtrm_amount": "전기금액(숫자만)",
      "bfefrmtrm_amount": "전전기금액(숫자만)"
    }},
    {{
      "account_nm": "부채총계",
      "thstrm_amount": "당기금액(숫자만)",
      "frmtrm_amount": "전기금액(숫자만)",
      "bfefrmtrm_amount": "전전기금액(숫자만)"
    }},
    ...
  ]
}}

중요:
- 금액은 원 단위 숫자로만 반환하고, 콤마나 단위(원, 천원, 백만원 등)는 제거해주세요.
- 단위가 "천원" 또는 "백만원"이면 해당 단위만큼 곱해서 원 단위로 변환해주세요.
  예: 1,000 (단위: 백만원) -> 1000000000
- 데이터가 없는 경우 "0"으로 표시해주세요.
- JSON 외의 다른 텍스트는 포함하지 마세요.
- 반드시 위 6개 항목을 모두 포함해주세요.
"""

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": "당신은 재무제표 분석 전문가입니다. 주어진 재무제표 테이블에서 정확한 숫자를 추출하여 JSON 형식으로 반환합니다."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 2000
            }

            logger.info("Sending request to Upstage API for financial extraction from HTML tables...")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=90.0
                )
                response.raise_for_status()
                data = response.json()

            if data.get("choices") and len(data["choices"]) > 0:
                result_text = data["choices"][0]["message"]["content"].strip()
                logger.info(f"Financial extraction result: {result_text[:200]}...")

                # JSON 파싱
                import json
                import re

                # JSON 부분만 추출
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    financial_data = json.loads(json_match.group())
                    logger.info(f"Successfully extracted {len(financial_data.get('items', []))} financial items")
                    return financial_data
                else:
                    logger.error("Failed to find JSON in LLM response")
                    raise LLMException("재무정보 추출 결과를 파싱할 수 없습니다.")
            else:
                logger.error("Empty response from Upstage API")
                raise LLMException("재무정보 추출 실패")

        except LLMException:
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during financial extraction: {e.response.status_code} - {e.response.text}")
            raise LLMException(f"재무정보 추출 실패: HTTP {e.response.status_code}")
        except Exception as e:
            logger.error(f"Financial extraction error: {str(e)}", exc_info=True)
            raise LLMException(f"재무정보 추출 실패: {str(e)}")
