"""Настройка логгера для приложения."""

import logging
import sys
from datetime import datetime
from typing import Optional

from config import Config


class CustomFormatter(logging.Formatter):
    """Кастомный форматтер для логов."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Форматирование записи лога."""
        # Получение UserID из extra, если есть
        user_id = getattr(record, 'user_id', None)
        user_info = f" (UserID: {user_id})" if user_id else ""
        
        # Форматирование времени
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        
        # Форматирование сообщения
        log_message = (
            f"[{timestamp}] "
            f"[{record.levelname}] "
            f"[{record.module}] - "
            f"{record.getMessage()}"
            f"{user_info}"
        )
        return log_message


def setup_logger(name: str = "RiskAnalyzerBot", user_id: Optional[int] = None) -> logging.Logger:
    """
    Настройка и возврат логгера.
    
    Args:
        name: Имя логгера
        user_id: ID пользователя Telegram (опционально)
    
    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper(), logging.DEBUG))
    
    # Удаление существующих обработчиков
    logger.handlers.clear()
    
    # Создание обработчика для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Применение кастомного форматтера
    formatter = CustomFormatter()
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    # Добавление user_id в контекст логгера
    if user_id:
        logger = logging.LoggerAdapter(logger, {"user_id": user_id})
    
    return logger


def get_logger(module_name: str, user_id: Optional[int] = None) -> logging.Logger:
    """
    Получение логгера для модуля.
    
    Args:
        module_name: Имя модуля
        user_id: ID пользователя Telegram (опционально)
    
    Returns:
        Логгер для модуля
    """
    return setup_logger(f"RiskAnalyzerBot.{module_name}", user_id)

