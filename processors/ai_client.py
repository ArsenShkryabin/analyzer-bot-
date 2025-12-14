"""Клиент для взаимодействия с API ИИ-сервиса анализа рисков."""

import json
import hashlib
from typing import Dict, Optional
import requests
from requests.exceptions import RequestException, Timeout

from config import Config
from logger import get_logger
from processors.risk_calculator import calculate_risk_fallback

logger = get_logger("ai_client")


def create_ai_prompt(project_params: Dict, model_results: Dict) -> str:
    """
    Создание промпта для ИИ-сервиса на основе данных проекта.
    
    Args:
        project_params: Параметры проекта
        model_results: Результаты финансовой модели
    
    Returns:
        Текст промпта для ИИ
    """
    prompt = f"""Ты - эксперт по анализу рисков инфраструктурных инвестиционных проектов. Проанализируй представленные данные финансовой модели проекта и оцени уровень рисков, включая анализ различных непредвиденных ситуаций.

Входные данные проекта:
- Тип проекта: {project_params.get('type', 'Не указан')}
- Стоимость строительства (CAPEX): {project_params.get('capex', 0)} млн руб
- Срок строительства: {project_params.get('construction_years', 0)} лет
- Доля долга: {project_params.get('debt_share', 0)}%
- Ставка по долгу: {project_params.get('debt_rate', 0)}%
- Ставка дисконтирования: {project_params.get('discount_rate', 0)}%

Результаты финансовой модели:
- NPV (чистая приведенная стоимость): {model_results.get('npv', 0)} млн руб
- IRR (внутренняя норма доходности): {model_results.get('irr', 0)}%
- Срок окупаемости: {model_results.get('payback_period', 0)} лет

Проведи комплексный анализ рисков, учитывая:
1. Финансовую устойчивость проекта (NPV, IRR, срок окупаемости)
2. Долговую нагрузку и стоимость заемного капитала
3. Временные риски (длительность строительства)
4. Специфику типа проекта

Проанализируй следующие непредвиденные ситуации и их влияние на проект:
- Превышение бюджета строительства на 20-50%
- Задержка сроков строительства на 1-3 года
- Изменение процентных ставок (рост ставки дисконтирования на 2-5%)
- Снижение доходов/тарифов на 15-30%
- Рост операционных расходов
- Форс-мажорные обстоятельства

Для каждой ситуации оцени:
- Ожидаемое влияние на NPV (млн руб)
- Ожидаемое влияние на IRR (%)
- Вероятность наступления (Низкая/Средняя/Высокая)
- Размер потенциальных убытков (млн руб)

Также предоставь:
- **Предложение дальнейшего видения бизнеса:** (минимум 7-10 предложений, включающих: 1) перспективы развития проекта, 2) возможности расширения и масштабирования, 3) стратегию роста, 4) долгосрочные цели, 5) конкурентные преимущества, 6) интеграцию с другими проектами/отраслями, 7) конкретные предложения по улучшению бизнеса и повышению эффективности, 8) рекомендации по оптимизации операционных процессов, 9) возможности диверсификации доходов, 10) меры по снижению рисков и повышению устойчивости проекта).
- **Примерную окупаемость этого бизнеса:** (число в годах).
- **Общую оценку бизнеса по 100-балльной шкале:** (число от 0 до 100).

ВАЖНО: Верни ответ ТОЛЬКО в формате валидного JSON, без дополнительного текста до или после JSON.

Верни ответ в строго следующем JSON формате:
{{
  "risk_level": "Низкий" | "Средний" | "Высокий" | "Критический",
  "reason": "Развернутое обоснование оценки (2-4 предложения)",
  "critical_factors": ["Фактор 1", "Фактор 2", ...],
  "scenarios": [
    {{
      "name": "Название сценария",
      "description": "Описание непредвиденной ситуации",
      "npv_impact": число (влияние на NPV в млн руб, может быть отрицательным),
      "irr_impact": число (влияние на IRR в процентах, может быть отрицательным),
      "probability": "Низкая" | "Средняя" | "Высокая",
      "potential_losses": число (потенциальные убытки в млн руб)
    }}
  ],
  "total_potential_losses": число (суммарные потенциальные убытки в млн руб),
  "risk_mitigation": ["Рекомендация 1", "Рекомендация 2", ...],
  "business_vision": "Предложение дальнейшего видения бизнеса (7-10 предложений, включая конкретные предложения по улучшению бизнеса, оптимизации процессов, диверсификации доходов и снижению рисков)",
  "estimated_payback": число (примерная окупаемость в годах),
  "business_score": число (оценка от 0 до 100)
}}

Оценка должна быть объективной и учитывать все представленные параметры. Сценарии должны быть реалистичными и специфичными для данного типа инфраструктурного проекта. Ответ должен быть ТОЛЬКО валидным JSON объектом."""
    
    return prompt


def analyze_risks(project_params: Dict, model_results: Dict) -> Dict:
    """
    Отправка запроса к API ИИ-сервиса для анализа рисков.
    
    Args:
        project_params: Параметры проекта
        model_results: Результаты финансовой модели
    
    Returns:
        Словарь с результатами анализа рисков
    
    Raises:
        RequestException: При ошибках HTTP-запроса
        ValueError: При невалидном ответе от API
    """
    logger.info("Формирование запроса к API ИИ-сервиса")
    
    # Создание промпта
    prompt = create_ai_prompt(project_params, model_results)
    
    # Формирование тела запроса в формате OpenAI API
    request_body = {
        "model": Config.AI_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "response_format": {"type": "json_object"}
    }
    
    logger.debug(f"Отправка запроса к API: {Config.AI_API_URL}")
    logger.debug(f"Упрощенный промпт (первые 200 символов): {prompt[:200]}...")
    
    # Подготовка заголовков
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Добавление API ключа, если указан
    if Config.AI_API_KEY:
        headers["Authorization"] = f"Bearer {Config.AI_API_KEY}"
        # Или можно использовать другой формат:
        # headers["X-API-Key"] = Config.AI_API_KEY
    
    # CORS заголовки для запроса (если API требует)
    headers["Origin"] = "RiskAnalyzerBot"
    
    try:
        # Нормализация данных для стабильности (округление до 2 знаков)
        normalized_params = {
            "capex": round(float(project_params.get('capex', 0)), 2),
            "construction_years": round(float(project_params.get('construction_years', 0)), 2),
            "debt_share": round(float(project_params.get('debt_share', 0)), 2),
            "debt_rate": round(float(project_params.get('debt_rate', 0)), 2),
            "discount_rate": round(float(project_params.get('discount_rate', 0)), 2)
        }
        normalized_results = {
            "npv": round(float(model_results.get('npv', 0)), 2),
            "irr": round(float(model_results.get('irr', 0)), 2),
            "payback_period": round(float(model_results.get('payback_period', 0)), 2)
        }
        
        # Генерация seed на основе нормализованных данных для стабильности
        data_string = json.dumps({
            **normalized_params,
            **normalized_results,
            "type": str(project_params.get('type', 'Не указан'))
        }, sort_keys=True)
        seed = int(hashlib.md5(data_string.encode()).hexdigest()[:8], 16) % 2147483647
        
        # Добавление seed для детерминированных результатов
        request_body["seed"] = seed
        
        logger.debug(f"Используется seed: {seed} для стабильности результатов")
        
        # Отправка POST запроса
        response = requests.post(
            Config.AI_API_URL,
            json=request_body,
            headers=headers,
            timeout=Config.API_TIMEOUT
        )
        
        logger.debug(f"Получен ответ от API: статус {response.status_code}")
        
        # Проверка статуса ответа
        if response.status_code == 200:
            try:
                api_response = response.json()
                logger.info("Успешно получен ответ от API ИИ-сервиса")
                
                # Извлечение JSON из ответа OpenAI API
                if "choices" in api_response and len(api_response["choices"]) > 0:
                    content = api_response["choices"][0]["message"]["content"]
                    # Парсинг JSON из текста ответа
                    result = json.loads(content)
                elif "risk_level" in api_response:
                    # Прямой ответ уже в нужном формате
                    result = api_response
                else:
                    raise ValueError("Неожиданный формат ответа от API")
                
                logger.debug(f"Уровень риска: {result.get('risk_level', 'Не указан')}")
                
                # Валидация структуры ответа
                if "risk_level" not in result:
                    logger.warning("Ответ API не содержит обязательное поле 'risk_level'")
                    raise ValueError("Невалидный формат ответа от API: отсутствует поле 'risk_level'")
                
                # Убеждаемся, что все необходимые поля присутствуют
                if "scenarios" not in result:
                    result["scenarios"] = []
                if "total_potential_losses" not in result:
                    result["total_potential_losses"] = 0
                if "risk_mitigation" not in result:
                    result["risk_mitigation"] = []
                if "business_vision" not in result:
                    result["business_vision"] = ""
                if "estimated_payback" not in result:
                    result["estimated_payback"] = None
                if "business_score" not in result:
                    result["business_score"] = None
                
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка парсинга JSON ответа: {e}")
                raise ValueError("Невалидный JSON в ответе от API")
        
        elif response.status_code == 400:
            # Обработка ошибок валидации (например, Invalid URL)
            try:
                error_data = response.json()
                error_message = error_data.get("error", {}).get("message", response.text)
            except:
                error_message = response.text
            logger.error(f"Ошибка валидации API (400): {error_message[:500]}")
            if "Invalid URL" in error_message or "GET" in error_message:
                logger.error("Обнаружена ошибка с методом запроса. Проверьте URL и метод.")
            raise RequestException(f"Ошибка API: {error_message[:200]}")
        
        elif response.status_code == 500:
            logger.error("Ошибка сервера API (500)")
            raise RequestException("Ошибка API: сервис анализа временно недоступен.")
        
        elif response.status_code == 503:
            logger.error("Сервис API недоступен (503)")
            raise RequestException("Ошибка API: сервис анализа временно недоступен.")
        
        else:
            logger.error(f"Неожиданный статус ответа: {response.status_code}")
            logger.error(f"Тело ответа: {response.text[:500]}")
            raise RequestException(
                f"Ошибка API: получен статус {response.status_code}. "
                "Сервис анализа временно недоступен."
            )
    
    except Timeout:
        logger.error(f"Превышено время ожидания ответа от API ({Config.API_TIMEOUT} сек)")
        raise RequestException("Ошибка обработки: превышено время ожидания.")
    
    except RequestException as e:
        logger.error(f"Ошибка HTTP-запроса к API: {e}", exc_info=True)
        raise RequestException("Ошибка API: сервис анализа временно недоступен.")
    
    except Exception as e:
        logger.error(f"Неожиданная ошибка при обращении к API: {e}", exc_info=True)
        raise RequestException("Ошибка API: произошла непредвиденная ошибка.")


def analyze_risks_with_fallback(project_params: Dict, model_results: Dict) -> Dict:
    """
    Анализ рисков с использованием fallback механизма при недоступности API.
    
    Args:
        project_params: Параметры проекта
        model_results: Результаты финансовой модели
    
    Returns:
        Словарь с результатами анализа рисков
    """
    try:
        return analyze_risks(project_params, model_results)
    except Exception as e:
        logger.warning(f"API недоступен, используется fallback механизм: {e}")
        
        # Объединение данных для fallback расчета
        all_data = {**project_params, **model_results}
        return calculate_risk_fallback(all_data)

