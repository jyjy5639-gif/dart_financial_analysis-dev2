import logging
import sys
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
import os
import glob


class LogManager:
    """로그 관리자 - 일별 로그 파일 생성 및 최대 개수 관리"""
    
    def __init__(self, log_dir: str, app_name: str, max_files: int = 100):
        """
        Args:
            log_dir: 로그 디렉토리 경로
            app_name: 애플리케이션 이름 (backend/frontend)
            max_files: 최대 로그 파일 개수
        """
        self.log_dir = Path(log_dir)
        self.app_name = app_name
        self.max_files = max_files
        
        # 로그 디렉토리 생성
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
    def cleanup_old_logs(self):
        """오래된 로그 파일 삭제 (최대 개수 초과 시)"""
        log_files = sorted(
            glob.glob(str(self.log_dir / "*.log")),
            key=os.path.getmtime
        )
        
        # 최대 개수 초과 시 오래된 파일부터 삭제
        if len(log_files) > self.max_files:
            files_to_delete = log_files[:len(log_files) - self.max_files]
            for file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    print(f"Deleted old log file: {file_path}")
                except Exception as e:
                    print(f"Error deleting log file {file_path}: {e}")
    
    def get_logger(self, name: str = None) -> logging.Logger:
        """로거 인스턴스 반환
        
        Args:
            name: 로거 이름 (기본값: app_name)
            
        Returns:
            설정된 로거 인스턴스
        """
        logger_name = name or self.app_name
        logger = logging.getLogger(logger_name)
        
        # 이미 핸들러가 설정되어 있으면 반환
        if logger.handlers:
            return logger
        
        logger.setLevel(logging.INFO)
        
        # 포맷터 설정
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 파일 핸들러 (일별 로테이션)
        log_file = self.log_dir / f"{self.app_name}_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = TimedRotatingFileHandler(
            filename=str(log_file),
            when='midnight',
            interval=1,
            backupCount=0,  # 백업 카운트는 cleanup_old_logs에서 관리
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        file_handler.suffix = "%Y%m%d"  # 로테이션 파일명 형식
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # 핸들러 추가
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # 오래된 로그 파일 정리
        self.cleanup_old_logs()
        
        return logger


# 백엔드 로거 인스턴스
def get_backend_logger(name: str = None) -> logging.Logger:
    """백엔드 로거 반환"""
    log_dir = Path(__file__).parent.parent.parent / "logs" / "backend"
    log_manager = LogManager(str(log_dir), "backend", max_files=100)
    return log_manager.get_logger(name)


# 프론트엔드 로거 인스턴스
def get_frontend_logger(name: str = None) -> logging.Logger:
    """프론트엔드 로거 반환"""
    log_dir = Path(__file__).parent.parent.parent / "logs" / "frontend"
    log_manager = LogManager(str(log_dir), "frontend", max_files=100)
    return log_manager.get_logger(name)
