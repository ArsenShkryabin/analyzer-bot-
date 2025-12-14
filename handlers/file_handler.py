"""Обработчик загрузки и обработки файлов от пользователей."""

from pathlib import Path
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes

from config import Config
from logger import get_logger
from processors.excel_reader import extract_project_data
from processors.ai_client import analyze_risks_with_fallback
from processors.report_generator import create_risk_analysis_sheet
from utils.cleanup import remove_file, cleanup_old_files

logger = get_logger("file_handler")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик загрузки документов от пользователей.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст бота
    """
    user = update.effective_user
    user_id = user.id if user else None
    document = update.message.document if update.message else None
    
    if not document:
        logger.warning(f"Получено сообщение без документа от пользователя {user_id}")
        await update.message.reply_text("Ошибка: не удалось получить файл.")
        return
    
    file_name = document.file_name or "unknown_file"
    file_id = document.file_id
    
    logger.info(f"Получен файл от пользователя {user_id}: {file_name} (ID: {file_id})")
    
    # Отправка подтверждения получения файла
    await update.message.reply_text("Файл получен. Начинаю обработку...")
    
    temp_file_path: Optional[Path] = None
    output_file_path: Optional[Path] = None
    
    try:
        # Валидация расширения файла
        if not file_name.lower().endswith('.xlsx'):
            error_msg = "Ошибка: поддерживаются только файлы Excel с расширением .xlsx"
            logger.warning(f"Неверное расширение файла: {file_name}")
            await update.message.reply_text(error_msg)
            return
        
        # Обеспечение существования директории для временных файлов
        Config.ensure_temp_dir()
        
        # Скачивание файла
        bot = context.bot
        file = await bot.get_file(file_id)
        
        temp_file_path = Config.TEMP_FILE_PATH / file_name
        await file.download_to_drive(temp_file_path)
        
        logger.info(f"Файл сохранен: {temp_file_path.name} (размер: {temp_file_path.stat().st_size} байт)")
        
        # Извлечение данных из Excel
        try:
            project_data = extract_project_data(temp_file_path)
            logger.info("Данные успешно извлечены из файла")
        except ValueError as e:
            error_msg = str(e)
            logger.error(f"Ошибка извлечения данных: {error_msg}")
            await update.message.reply_text(f"Ошибка: {error_msg}")
            return
        except Exception as e:
            error_msg = "Ошибка: не удалось прочитать файл. Убедитесь, что файл не поврежден."
            logger.error(f"Ошибка чтения файла: {e}", exc_info=True)
            await update.message.reply_text(error_msg)
            return
        
        # Разделение данных на параметры проекта и результаты модели
        project_params = {
            "type": project_data.get("type", "Не указан"),
            "capex": project_data.get("capex", 0),
            "construction_years": project_data.get("construction_years", 0),
            "debt_share": project_data.get("debt_share", 0),
            "debt_rate": project_data.get("debt_rate", 0),
            "discount_rate": project_data.get("discount_rate", 0)
        }
        
        model_results = {
            "npv": project_data.get("npv", 0),
            "irr": project_data.get("irr", 0),
            "payback_period": project_data.get("payback_period", 0)
        }
        
        logger.debug(f"Параметры проекта: {project_params}")
        logger.debug(f"Результаты модели: {model_results}")
        
        # Анализ рисков через ИИ-сервис
        try:
            logger.info("Отправка запроса к API ИИ-сервиса")
            risk_analysis = analyze_risks_with_fallback(project_params, model_results)
            logger.info(f"Анализ рисков завершен. Уровень риска: {risk_analysis.get('risk_level', 'Не определен')}")
        except Exception as e:
            error_msg = "Ошибка API: сервис анализа временно недоступен."
            logger.error(f"Ошибка при обращении к API: {e}", exc_info=True)
            await update.message.reply_text(error_msg)
            return
        
        # Генерация отчета
        try:
            logger.info("Создание отчета анализа рисков")
            output_file_path = create_risk_analysis_sheet(
                temp_file_path,
                project_params,
                model_results,
                risk_analysis
            )
            logger.info(f"Отчет создан: {output_file_path.name}")
        except Exception as e:
            error_msg = f"Ошибка генерации отчета: {str(e)}"
            logger.error(f"Ошибка создания отчета: {e}", exc_info=True)
            await update.message.reply_text(error_msg)
            return
        
        # Отправка результата пользователю
        try:
            logger.info(f"Отправка файла пользователю {user_id}")
            with open(output_file_path, 'rb') as report_file:
                await update.message.reply_document(
                    document=report_file,
                    filename=output_file_path.name,
                    caption="✅ Анализ рисков завершен. Файл с результатами готов."
                )
            logger.info("Файл успешно отправлен пользователю")
            
            # Отправка дополнительного сообщения с видением и оценкой
            business_vision = risk_analysis.get("business_vision", "")
            business_score = risk_analysis.get("business_score")
            estimated_payback = risk_analysis.get("estimated_payback")
            
            logger.debug(f"Данные для дополнительного сообщения: vision={bool(business_vision)}, score={business_score}, payback={estimated_payback}")
            
            # Отправляем сообщение, если есть хотя бы одно поле
            if business_vision or business_score is not None or estimated_payback is not None:
                try:
                    # Используем базовый срок окупаемости из модели, если estimated_payback не указан
                    display_payback = estimated_payback if estimated_payback is not None else model_results.get("payback_period")
                    
                    vision_message = "📊 **Оценка бизнеса:**\n\n"
                    
                    if business_score is not None:
                        # Определяем уровень оценки
                        if business_score >= 80:
                            score_emoji = "🟢"
                            score_level = "Отличный"
                            score_explanation = "Проект демонстрирует высокую инвестиционную привлекательность с отличными финансовыми показателями и низкими рисками."
                        elif business_score >= 60:
                            score_emoji = "🟡"
                            score_level = "Хороший"
                            score_explanation = "Проект имеет хорошие перспективы, но требует внимательного мониторинга ключевых рисков."
                        elif business_score >= 40:
                            score_emoji = "🟠"
                            score_level = "Удовлетворительный"
                            score_explanation = "Проект имеет среднюю привлекательность и требует дополнительных мер по снижению рисков."
                        else:
                            score_emoji = "🔴"
                            score_level = "Требует внимания"
                            score_explanation = "Проект имеет высокие риски и требует серьезной доработки финансовой модели."
                        
                        vision_message += f"{score_emoji} **Общая оценка:** {business_score}/100 ({score_level})\n"
                        vision_message += f"_{score_explanation}_\n\n"
                    
                    # Добавляем ключевые показатели для контекста
                    vision_message += "**Ключевые показатели:**\n"
                    vision_message += f"• NPV: {model_results.get('npv', 0):.2f} млн руб\n"
                    vision_message += f"• IRR: {model_results.get('irr', 0):.2f}%\n"
                    vision_message += f"• Срок окупаемости: {model_results.get('payback_period', 0):.2f} лет\n\n"
                    
                    if business_vision:
                        vision_message += f"💡 **Видение бизнеса:**\n{business_vision}\n\n"
                    
                    if display_payback is not None:
                        if estimated_payback is not None and estimated_payback != model_results.get('payback_period'):
                            vision_message += f"⏱️ **Примерная окупаемость (с учетом перспектив):** {display_payback:.2f} лет\n\n"
                    
                    vision_message += "📄 Подробный анализ доступен в прикрепленном файле."
                    
                    # Разбиваем длинные сообщения (лимит Telegram - 4096 символов)
                    max_length = 4000
                    if len(vision_message) > max_length:
                        # Отправляем первую часть
                        first_part = vision_message[:max_length]
                        last_newline = first_part.rfind('\n')
                        if last_newline > max_length * 0.8:  # Если есть разумное место для разрыва
                            first_part = vision_message[:last_newline]
                            second_part = vision_message[last_newline+1:]
                        else:
                            second_part = vision_message[max_length:]
                        
                        await update.message.reply_text(first_part, parse_mode='Markdown')
                        if second_part.strip():
                            await update.message.reply_text(second_part, parse_mode='Markdown')
                        logger.info("Дополнительное сообщение с видением отправлено (разбито на части)")
                    else:
                        # Отправляем с Markdown форматированием
                        await update.message.reply_text(vision_message, parse_mode='Markdown')
                        logger.info("Дополнительное сообщение с видением отправлено")
                except Exception as e:
                    logger.error(f"Ошибка при отправке дополнительного сообщения: {e}", exc_info=True)
            else:
                logger.warning("Нет данных для дополнительного сообщения (business_vision, business_score, estimated_payback)")
                
        except Exception as e:
            error_msg = "Ошибка отправки файла. Попробуйте позже."
            logger.error(f"Ошибка отправки файла: {e}", exc_info=True)
            await update.message.reply_text(error_msg)
            return
        
        # Очистка временных файлов
        logger.info("Очистка временных файлов")
        if temp_file_path:
            remove_file(temp_file_path)
        if output_file_path:
            # Оставляем выходной файл на некоторое время, затем удаляем
            # В реальном сценарии можно оставить его для пользователя
            pass
        
        # Периодическая очистка старых файлов
        cleanup_old_files(max_age_minutes=5)
        
        logger.info(f"Обработка файла завершена успешно для пользователя {user_id}")
        
    except Exception as e:
        error_msg = "Ошибка обработки: произошла непредвиденная ошибка."
        logger.error(f"Критическая ошибка при обработке файла: {e}", exc_info=True)
        await update.message.reply_text(error_msg)
        
        # Очистка в случае ошибки
        if temp_file_path:
            remove_file(temp_file_path)
        if output_file_path:
            remove_file(output_file_path)

