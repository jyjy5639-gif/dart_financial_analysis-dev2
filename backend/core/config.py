from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # API Keys
    dart_api_key: str = ""
    gemini_api_key: str = ""
    openai_api_key: str = ""
    claude_api_key: str = ""
    upstage_api_key: str = ""
    
    # Backend Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_url: str = "http://localhost:8000"
    
    # Frontend Server
    frontend_host: str = "0.0.0.0"
    frontend_port: int = 8501
    
    # CORS - 환경변수에서 읽을 때는 콤마로 구분
    allowed_origins: str = "http://localhost:8501,http://127.0.0.1:8501"
    
    @property
    def cors_origins(self) -> List[str]:
        """CORS origins를 리스트로 반환"""
        return [origin.strip() for origin in self.allowed_origins.split(',')]
    
    # DART API
    dart_base_url: str = "https://opendart.fss.or.kr/api"
    
    # KRX
    krx_url: str = "https://kind.krx.co.kr/corpgeneral/corpList.do"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
