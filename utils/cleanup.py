"""Утилиты для очистки временных файлов."""

import os
import time
from pathlib import Path
from typing import Optional

from config import Config
from logger import get_logger

logger = get_logger("cleanup")


def remove_file(file_path: Path) -> bool:
    """
    Удаление одного файла.
    
    Args:
        file_path: Путь к файлу для удаления
    
    Returns:
        True если файл успешно удален, False в противном случае
    """
    try:
        if file_path.exists():
            file_path.unlink()
            logger.debug(f"Файл удален: {file_path.name}")
            return True
        else:
            logger.debug(f"Файл не существует: {file_path.name}")
            return False
    except Exception as e:
        logger.error(f"Ошибка при удалении файла {file_path.name}: {e}", exc_info=True)
        return False


def cleanup_old_files(max_age_minutes: int = 5) -> int:
    """
    Удаление временных файлов старше указанного возраста.
    
    Args:
        max_age_minutes: Максимальный возраст файла в минутах
    
    Returns:
        Количество удаленных файлов
    """
    if not Config.TEMP_FILE_PATH.exists():
        logger.debug("Директория временных файлов не существует")
        return 0
    
    current_time = time.time()
    max_age_seconds = max_age_minutes * 60
    deleted_count = 0
    
    try:
        for file_path in Config.TEMP_FILE_PATH.iterdir():
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                
                if file_age > max_age_seconds:
                    if remove_file(file_path):
                        deleted_count += 1
                        logger.info(f"Удален устаревший файл: {file_path.name} (возраст: {file_age/60:.1f} мин)")
        
        if deleted_count > 0:
            logger.info(f"Очищено временных файлов: {deleted_count}")
        
        return deleted_count
        
    except Exception as e:
        logger.error(f"Ошибка при очистке временных файлов: {e}", exc_info=True)
        return deleted_count


def cleanup_file_after_processing(file_path: Optional[Path], delay_seconds: int = 0) -> None:
    """
    Удаление файла после обработки с возможной задержкой.
    
    Args:
        file_path: Путь к файлу для удаления
        delay_seconds: Задержка перед удалением в секундах
    """
    if file_path is None:
        return
    
    if delay_seconds > 0:
        time.sleep(delay_seconds)
    
    remove_file(file_path)


def cleanup_all_temp_files() -> int:
    """
    Удаление всех файлов из временной директории.
    
    Returns:
        Количество удаленных файлов
    """
    if not Config.TEMP_FILE_PATH.exists():
        return 0
    
    deleted_count = 0
    
    try:
        for file_path in Config.TEMP_FILE_PATH.iterdir():
            if file_path.is_file():
                if remove_file(file_path):
                    deleted_count += 1
        
        logger.info(f"Удалено всех временных файлов: {deleted_count}")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Ошибка при полной очистке временных файлов: {e}", exc_info=True)
        return deleted_count

