from typing import Dict
from openai import AsyncOpenAI
from .base import BaseLLMProvider
from ..exceptions import LLMException
from ..logger import get_backend_logger

logger = get_backend_logger("llm.openai")


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT LLM 제공자"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.client = AsyncOpenAI(api_key=api_key)
        self.model_name = "gpt-4o-mini"
        logger.info(f"OpenAI provider initialized with model: {self.model_name}")
    
    async def generate_briefing(
        self,
        corp_name: str,
        financial_data: Dict,
        style: str = "default"
    ) -> str:
        """GPT로 재무 브리핑 생성"""
        
        try:
            logger.info(f"Generating briefing for {corp_name} with style: {style}")
            prompt = self._build_prompt(corp_name, financial_data, style)
            logger.info(f"Prompt length: {len(prompt)} characters")
            
            logger.info("Sending request to OpenAI API...")
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "당신은 재무 분석 전문가입니다. 반드시 한글로만 답변하세요."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            if response.choices and response.choices[0].message.content:
                briefing_text = response.choices[0].message.content.strip()
                logger.info(f"Successfully generated briefing: {len(briefing_text)} characters")
                
                # 텍스트 유효성 검증
                if len(briefing_text) < 100:
                    logger.warning(f"Briefing text is too short: {len(briefing_text)} chars")
                    raise LLMException("생성된 브리핑이 너무 짧습니다. 다시 시도해주세요.")
                
                return briefing_text
            else:
                logger.error("Received empty response from OpenAI API")
                raise LLMException("OpenAI API로부터 응답을 받지 못했습니다.")
                
        except LLMException:
            raise
        except Exception as e:
            error_msg = str(e)
            logger.error(f"OpenAI API error: {error_msg}", exc_info=True)
            
            if "rate_limit" in error_msg.lower():
                raise LLMException("API 사용량 한도 초과. 잠시 후 다시 시도하세요.")
            elif "invalid_api_key" in error_msg.lower() or "authentication" in error_msg.lower():
                raise LLMException(
                    "유효하지 않은 API 키입니다.\n"
                    "발급: https://platform.openai.com/api-keys"
                )
            elif "insufficient_quota" in error_msg.lower():
                raise LLMException("API 크레딧이 부족합니다. 크레딧을 충전해주세요.")
            else:
                raise LLMException(f"브리핑 생성 실패: {error_msg}")
    
    def is_available(self) -> bool:
        """OpenAI API 사용 가능 여부"""
        return bool(self.api_key)
