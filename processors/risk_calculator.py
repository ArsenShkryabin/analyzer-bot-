"""Модуль для расчета уровня рисков проекта (fallback механизм)."""

from typing import Dict, Literal


def calculate_risk_score(
    npv: float,
    irr: float,
    payback_period: float,
    debt_share: float,
    debt_rate: float,
    construction_years: float,
    discount_rate: float
) -> int:
    """
    Расчет количественной оценки риска (risk_score от 0 до 100).
    
    Args:
        npv: Чистая приведенная стоимость, млн руб
        irr: Внутренняя норма доходности, %
        payback_period: Срок окупаемости, лет
        debt_share: Доля долга, %
        debt_rate: Ставка по долгу, %
        construction_years: Срок строительства, лет
        discount_rate: Ставка дисконтирования, %
    
    Returns:
        Risk score от 0 до 100
    """
    risk_score = 0
    
    # 1. Финансовая устойчивость (вес 40%)
    if npv < 0:
        risk_score += 40
    elif npv < 50:
        risk_score += 20
    
    if irr < discount_rate:
        risk_score += 30
    elif irr < discount_rate * 1.1:
        risk_score += 15
    
    if payback_period > 15:
        risk_score += 30
    elif payback_period > 10:
        risk_score += 20
    
    # 2. Долговая нагрузка (вес 30%)
    if debt_share > 70:
        risk_score += 35
    elif debt_share > 50:
        risk_score += 25
    
    if debt_rate > 20:
        risk_score += 30
    elif debt_rate > 15:
        risk_score += 20
    
    # 3. Временные риски (вес 20%)
    if construction_years > 7:
        risk_score += 25
    elif construction_years > 5:
        risk_score += 15
    
    # 4. Ставка дисконтирования (вес 10%)
    if discount_rate > 25:
        risk_score += 20
    elif discount_rate > 20:
        risk_score += 10
    
    return min(100, risk_score)


def score_to_risk_level(risk_score: int) -> Literal["Низкий", "Средний", "Высокий", "Критический"]:
    """
    Преобразование количественного score в уровень риска.
    
    Args:
        risk_score: Количественная оценка риска (0-100)
    
    Returns:
        Уровень риска
    """
    if risk_score <= 30:
        return "Низкий"
    elif risk_score <= 60:
        return "Средний"
    elif risk_score <= 85:
        return "Высокий"
    else:
        return "Критический"


def calculate_risk_fallback(project_data: Dict) -> Dict:
    """
    Расчет рисков как fallback механизм, если API недоступен.
    
    Args:
        project_data: Словарь с параметрами проекта и результатами модели
    
    Returns:
        Словарь с оценкой рисков в формате, совместимом с API ответом
    """
    risk_score = calculate_risk_score(
        npv=project_data.get("npv", 0),
        irr=project_data.get("irr", 0),
        payback_period=project_data.get("payback_period", 0),
        debt_share=project_data.get("debt_share", 0),
        debt_rate=project_data.get("debt_rate", 0),
        construction_years=project_data.get("construction_years", 0),
        discount_rate=project_data.get("discount_rate", 0)
    )
    
    risk_level = score_to_risk_level(risk_score)
    
    # Формирование обоснования на основе score
    if risk_level == "Низкий":
        reason = "Проект демонстрирует хорошие финансовые показатели и низкий уровень рисков."
    elif risk_level == "Средний":
        reason = "Проект имеет приемлемый уровень рисков, но требует внимательного мониторинга ключевых параметров."
    elif risk_level == "Высокий":
        reason = "Проект характеризуется высоким уровнем рисков, необходимы меры по их снижению."
    else:
        reason = "Проект имеет критический уровень рисков, требует пересмотра параметров или отказа от реализации."
    
    # Определение критических факторов
    critical_factors = []
    if project_data.get("npv", 0) < 0:
        critical_factors.append("Отрицательный NPV")
    if project_data.get("irr", 0) < project_data.get("discount_rate", 0):
        critical_factors.append("IRR ниже ставки дисконтирования")
    if project_data.get("debt_share", 0) > 50:
        critical_factors.append("Высокая доля долга")
    if project_data.get("payback_period", 0) > 10:
        critical_factors.append("Долгий срок окупаемости")
    
    return {
        "risk_level": risk_level,
        "reason": reason,
        "critical_factors": critical_factors if critical_factors else ["Требуется детальный анализ"],
        "scenarios": [],
        "total_potential_losses": 0,
        "risk_mitigation": []
    }

