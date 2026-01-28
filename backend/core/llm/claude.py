from typing import Dict
from anthropic import AsyncAnthropic
from .base import BaseLLMProvider
from ..exceptions import LLMException
from ..logger import get_backend_logger

logger = get_backend_logger("llm.claude")


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude LLM 제공자"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.client = AsyncAnthropic(api_key=api_key)
        self.model_name = "claude-sonnet-4-5"
        logger.info(f"Claude provider initialized with model: {self.model_name}")
    
    async def generate_briefing(
        self,
        corp_name: str,
        financial_data: Dict,
        style: str = "default"
    ) -> str:
        """Claude로 재무 브리핑 생성"""
        
        try:
            logger.info(f"Generating briefing for {corp_name} with style: {style}")
            prompt = self._build_prompt(corp_name, financial_data, style)
            logger.info(f"Prompt length: {len(prompt)} characters")
            
            logger.info("Sending request to Claude API...")
            response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=4000,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            if response.content and len(response.content) > 0:
                briefing_text = response.content[0].text.strip()
                logger.info(f"Successfully generated briefing: {len(briefing_text)} characters")
                
                # 텍스트 유효성 검증
                if len(briefing_text) < 100:
                    logger.warning(f"Briefing text is too short: {len(briefing_text)} chars")
                    raise LLMException("생성된 브리핑이 너무 짧습니다. 다시 시도해주세요.")
                
                return briefing_text
            else:
                logger.error("Received empty response from Claude API")
                raise LLMException("Claude API로부터 응답을 받지 못했습니다.")
                
        except LLMException:
            raise
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Claude API error: {error_msg}", exc_info=True)
            
            if "rate_limit" in error_msg.lower():
                raise LLMException("API 사용량 한도 초과. 잠시 후 다시 시도하세요.")
            elif "authentication" in error_msg.lower() or "invalid" in error_msg.lower():
                raise LLMException(
                    "유효하지 않은 API 키입니다.\n"
                    "발급: https://console.anthropic.com/"
                )
            elif "credit" in error_msg.lower() or "quota" in error_msg.lower():
                raise LLMException("API 크레딧이 부족합니다. 크레딧을 충전해주세요.")
            else:
                raise LLMException(f"브리핑 생성 실패: {error_msg}")
    
    def is_available(self) -> bool:
        """Claude API 사용 가능 여부"""
        return bool(self.api_key)
