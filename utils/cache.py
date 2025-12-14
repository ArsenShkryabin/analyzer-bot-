"""Модуль для кэширования результатов анализа рисков."""

import hashlib
import json
import pickle
from pathlib import Path
from typing import Dict, Optional
import time

from config import Config
from logger import get_logger

logger = get_logger("cache")


class AnalysisCache:
    """Класс для кэширования результатов анализа рисков."""
    
    def __init__(self, cache_dir: Optional[Path] = None, ttl_hours: int = 24):
        """
        Инициализация кэша.
        
        Args:
            cache_dir: Директория для хранения кэша (по умолчанию ./cache)
            ttl_hours: Время жизни кэша в часах (по умолчанию 24 часа)
        """
        self.cache_dir = cache_dir or Path("./cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_hours * 3600
        logger.info(f"Кэш инициализирован: {self.cache_dir}, TTL: {ttl_hours} часов")
    
    def _generate_cache_key(self, project_params: Dict, model_results: Dict) -> str:
        """
        Генерация ключа кэша на основе входных данных.
        
        Args:
            project_params: Параметры проекта
            model_results: Результаты финансовой модели
        
        Returns:
            Хеш-ключ для кэша
        """
        # Создаем словарь с нормализованными данными
        cache_data = {
            "project_params": {
                "type": str(project_params.get("type", "")).strip(),
                "capex": round(float(project_params.get("capex", 0)), 2),
                "construction_years": round(float(project_params.get("construction_years", 0)), 2),
                "debt_share": round(float(project_params.get("debt_share", 0)), 2),
                "debt_rate": round(float(project_params.get("debt_rate", 0)), 2),
                "discount_rate": round(float(project_params.get("discount_rate", 0)), 2)
            },
            "model_results": {
                "npv": round(float(model_results.get("npv", 0)), 2),
                "irr": round(float(model_results.get("irr", 0)), 2),
                "payback_period": round(float(model_results.get("payback_period", 0)), 2)
            }
        }
        
        # Создаем JSON строку и хеш
        json_str = json.dumps(cache_data, sort_keys=True, ensure_ascii=False)
        cache_key = hashlib.sha256(json_str.encode('utf-8')).hexdigest()
        
        logger.debug(f"Сгенерирован ключ кэша: {cache_key[:16]}...")
        return cache_key
    
    def get(self, project_params: Dict, model_results: Dict) -> Optional[Dict]:
        """
        Получение результата из кэша.
        
        Args:
            project_params: Параметры проекта
            model_results: Результаты финансовой модели
        
        Returns:
            Результат анализа из кэша или None
        """
        cache_key = self._generate_cache_key(project_params, model_results)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if not cache_file.exists():
            logger.debug("Кэш не найден")
            return None
        
        try:
            # Проверяем время жизни кэша
            file_age = time.time() - cache_file.stat().st_mtime
            if file_age > self.ttl_seconds:
                logger.debug(f"Кэш устарел (возраст: {file_age/3600:.1f} часов)")
                cache_file.unlink()
                return None
            
            # Загружаем данные из кэша
            with open(cache_file, 'rb') as f:
                cached_data = pickle.load(f)
            
            logger.info(f"Результат загружен из кэша (ключ: {cache_key[:16]}...)")
            return cached_data
            
        except Exception as e:
            logger.warning(f"Ошибка при чтении кэша: {e}")
            # Удаляем поврежденный файл
            try:
                cache_file.unlink()
            except:
                pass
            return None
    
    def set(self, project_params: Dict, model_results: Dict, analysis_result: Dict) -> None:
        """
        Сохранение результата в кэш.
        
        Args:
            project_params: Параметры проекта
            model_results: Результаты финансовой модели
            analysis_result: Результат анализа рисков
        """
        cache_key = self._generate_cache_key(project_params, model_results)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(analysis_result, f)
            
            logger.info(f"Результат сохранен в кэш (ключ: {cache_key[:16]}...)")
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении в кэш: {e}", exc_info=True)
    
    def clear_old(self) -> int:
        """
        Очистка устаревших записей кэша.
        
        Returns:
            Количество удаленных файлов
        """
        if not self.cache_dir.exists():
            return 0
        
        deleted_count = 0
        current_time = time.time()
        
        try:
            for cache_file in self.cache_dir.glob("*.pkl"):
                file_age = current_time - cache_file.stat().st_mtime
                if file_age > self.ttl_seconds:
                    cache_file.unlink()
                    deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"Очищено устаревших записей кэша: {deleted_count}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Ошибка при очистке кэша: {e}", exc_info=True)
            return deleted_count


# Глобальный экземпляр кэша
_cache_instance: Optional[AnalysisCache] = None


def get_cache() -> AnalysisCache:
    """Получение глобального экземпляра кэша."""
    global _cache_instance
    if _cache_instance is None:
        cache_dir = Path(Config.TEMP_FILE_PATH.parent / "cache")
        _cache_instance = AnalysisCache(cache_dir=cache_dir, ttl_hours=24)
    return _cache_instance

