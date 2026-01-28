from typing import Dict
import google.generativeai as genai
from .base import BaseLLMProvider
from ..exceptions import LLMException
from ..logger import get_backend_logger

logger = get_backend_logger("llm.gemini")


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM 제공자"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        genai.configure(api_key=api_key)
        # gemini-2.0-flash-exp 대신 안정적인 gemini-1.5-flash 사용
        self.model_name = 'gemini-2.5-flash'
        logger.info(f"Gemini provider initialized with model: {self.model_name}")
    
    async def generate_briefing(
        self,
        corp_name: str,
        financial_data: Dict,
        style: str = "default"
    ) -> str:
        """Gemini로 재무 브리핑 생성"""
        
        try:
            logger.info(f"Generating briefing for {corp_name} with style: {style}")
            prompt = self._build_prompt(corp_name, financial_data, style)
            logger.info(f"Prompt length: {len(prompt)} characters")
            
            model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=8000,  # 4000 -> 8000으로 증가
                )
            )
            
            logger.info("Sending request to Gemini API...")
            response = model.generate_content(prompt)
            
            # 응답 검증
            if not response:
                logger.error("Received empty response from Gemini API")
                raise LLMException("Gemini API로부터 응답을 받지 못했습니다.")
            
            # 응답 텍스트 추출
            if hasattr(response, 'text') and response.text:
                briefing_text = response.text.strip()
                logger.info(f"Successfully generated briefing: {len(briefing_text)} characters")
                
                # 텍스트 유효성 검증
                if len(briefing_text) < 100:
                    logger.warning(f"Briefing text is too short: {len(briefing_text)} chars")
                    raise LLMException("생성된 브리핑이 너무 짧습니다. 다시 시도해주세요.")
                
                # 이상한 문자열 패턴 검증
                if briefing_text.count('–') > 50 or briefing_text.count('WH') > 20:
                    logger.error("Generated text contains suspicious patterns")
                    raise LLMException("비정상적인 응답이 생성되었습니다. 다시 시도해주세요.")
                
                return briefing_text
            
            # candidates 확인
            elif hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    parts = candidate.content.parts
                    if parts and hasattr(parts[0], 'text'):
                        briefing_text = parts[0].text.strip()
                        logger.info(f"Extracted text from candidates: {len(briefing_text)} chars")
                        
                        if len(briefing_text) < 100:
                            raise LLMException("생성된 브리핑이 너무 짧습니다.")
                        
                        return briefing_text
            
            # 응답을 파싱할 수 없음
            logger.error(f"Unable to parse Gemini response: {response}")
            raise LLMException("Gemini API 응답을 파싱할 수 없습니다.")
                
        except LLMException:
            raise
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Gemini API error: {error_msg}", exc_info=True)
            
            if "429" in error_msg or "quota" in error_msg.lower():
                raise LLMException(
                    "API 일일 한도 초과. 내일 다시 시도하세요.\n"
                    "일일 한도: 1500회/일 (무료 버전)"
                )
            elif "403" in error_msg or "permission" in error_msg.lower():
                raise LLMException(
                    "API 키 오류. API 키를 다시 확인하세요.\n"
                    "발급: https://aistudio.google.com/app/apikeys"
                )
            elif "SAFETY" in error_msg.upper():
                raise LLMException(
                    "안전성 필터로 인해 응답이 차단되었습니다. 다시 시도해주세요."
                )
            else:
                raise LLMException(f"브리핑 생성 실패: {error_msg}")
    
    def is_available(self) -> bool:
        """Gemini API 사용 가능 여부"""
        return bool(self.api_key)
