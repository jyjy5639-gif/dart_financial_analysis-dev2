from typing import Dict
from backend.core.llm import (
    BaseLLMProvider,
    GeminiProvider,
    OpenAIProvider,
    ClaudeProvider,
    UpstageProvider
)
from backend.core.exceptions import LLMException
from backend.core.config import settings


class LLMService:
    """LLM 통합 서비스"""
    
    def __init__(self):
        self.providers: Dict[str, BaseLLMProvider] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """사용 가능한 LLM 프로바이더 초기화"""
        
        # Gemini
        if settings.gemini_api_key:
            self.providers['gemini'] = GeminiProvider(settings.gemini_api_key)
        
        # OpenAI
        if settings.openai_api_key:
            self.providers['openai'] = OpenAIProvider(settings.openai_api_key)
        
        # Claude
        if settings.claude_api_key:
            self.providers['claude'] = ClaudeProvider(settings.claude_api_key)
        
        # Upstage
        if settings.upstage_api_key:
            self.providers['upstage'] = UpstageProvider(settings.upstage_api_key)
    
    def register_provider(self, name: str, api_key: str):
        """프로바이더 동적 등록"""
        provider_classes = {
            'gemini': GeminiProvider,
            'openai': OpenAIProvider,
            'claude': ClaudeProvider,
            'upstage': UpstageProvider
        }
        
        if name not in provider_classes:
            raise LLMException(f"알 수 없는 프로바이더: {name}")
        
        provider_class = provider_classes[name]
        self.providers[name] = provider_class(api_key)
    
    def get_available_providers(self) -> list:
        """사용 가능한 프로바이더 목록"""
        return [
            name for name, provider in self.providers.items()
            if provider.is_available()
        ]
    
    async def generate_briefing(
        self,
        provider_name: str,
        corp_name: str,
        financial_data: Dict,
        style: str = "default"
    ) -> str:
        """재무 브리핑 생성
        
        Args:
            provider_name: LLM 프로바이더 이름
            corp_name: 회사명
            financial_data: 재무 데이터
            style: 브리핑 스타일
            
        Returns:
            생성된 브리핑 텍스트
        """
        provider = self.providers.get(provider_name)
        
        if not provider:
            raise LLMException(
                f"알 수 없는 프로바이더: {provider_name}\n"
                f"사용 가능: {', '.join(self.get_available_providers())}"
            )
        
        if not provider.is_available():
            raise LLMException(f"{provider_name} API 키가 설정되지 않았습니다.")
        
        return await provider.generate_briefing(corp_name, financial_data, style)
