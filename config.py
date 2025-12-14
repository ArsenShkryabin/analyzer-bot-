"""Загрузка конфигурации из переменных окружения."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()


class Config:
    """Класс для хранения конфигурации приложения."""
    
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # AI API Configuration
    AI_API_URL: str = os.getenv("AI_API_URL", "")
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")
    AI_MODEL: str = os.getenv("AI_MODEL", "gpt-4o")
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG")
    
    # Temporary Files Path
    TEMP_FILE_PATH: Path = Path(os.getenv("TEMP_FILE_PATH", "./temp_files"))
    
    # API Request Timeout (seconds)
    API_TIMEOUT: int = int(os.getenv("API_TIMEOUT", "180"))
    
    @classmethod
    def validate(cls) -> bool:
        """Проверка наличия обязательных параметров конфигурации."""
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен в переменных окружения")
        if not cls.AI_API_URL:
            raise ValueError("AI_API_URL не установлен в переменных окружения")
        return True
    
    @classmethod
    def ensure_temp_dir(cls) -> None:
        """Создание директории для временных файлов, если её нет."""
        cls.TEMP_FILE_PATH.mkdir(parents=True, exist_ok=True)

