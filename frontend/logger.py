import logging
import sys
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
import os
import glob


class FrontendLogManager:
    """프론트엔드 로그 관리자"""
    
    def __init__(self, log_dir: str, max_files: int = 100):
        """
        Args:
            log_dir: 로그 디렉토리 경로
            max_files: 최대 로그 파일 개수
        """
        self.log_dir = Path(log_dir)
        self.max_files = max_files
        
        # 로그 디렉토리 생성
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
    def cleanup_old_logs(self):
        """오래된 로그 파일 삭제"""
        log_files = sorted(
            glob.glob(str(self.log_dir / "*.log")),
            key=os.path.getmtime
        )
        
        if len(log_files) > self.max_files:
            files_to_delete = log_files[:len(log_files) - self.max_files]
            for file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    print(f"Deleted old log file: {file_path}")
                except Exception as e:
                    print(f"Error deleting log file {file_path}: {e}")
    
    def get_logger(self, name: str = "frontend") -> logging.Logger:
        """로거 인스턴스 반환"""
        logger = logging.getLogger(name)
        
        if logger.handlers:
            return logger
        
        logger.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(name)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 파일 핸들러
        log_file = self.log_dir / f"frontend_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = TimedRotatingFileHandler(
            filename=str(log_file),
            when='midnight',
            interval=1,
            backupCount=0,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        file_handler.suffix = "%Y%m%d"
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        self.cleanup_old_logs()
        
        return logger


def get_logger(name: str = "frontend") -> logging.Logger:
    """프론트엔드 로거 반환"""
    log_dir = Path(__file__).parent.parent / "logs" / "frontend"
    log_manager = FrontendLogManager(str(log_dir), max_files=100)
    return log_manager.get_logger(name)
