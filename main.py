"""Главный модуль для запуска Telegram бота RiskAnalyzerBot."""

import asyncio
import sys
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config import Config
from logger import setup_logger
from handlers.file_handler import handle_document
from handlers.message_handler import start_command, help_command, handle_text_message
from utils.cleanup import cleanup_old_files

# Настройка логгера
logger = setup_logger("RiskAnalyzerBot")


def main() -> None:
    """Основная функция запуска бота."""
    try:
        # Валидация конфигурации
        logger.info("Проверка конфигурации...")
        Config.validate()
        Config.ensure_temp_dir()
        logger.info("Конфигурация валидна")
        
        # Очистка старых временных файлов при запуске
        logger.info("Очистка старых временных файлов...")
        deleted = cleanup_old_files(max_age_minutes=5)
        if deleted > 0:
            logger.info(f"Удалено {deleted} устаревших файлов")
        
        # Создание приложения бота
        logger.info("Инициализация Telegram бота...")
        application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
        
        # Регистрация обработчиков команд
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        
        # Регистрация обработчика документов (Excel файлы)
        application.add_handler(
            MessageHandler(filters.Document.ALL & filters.Document.FileExtension("xlsx"), handle_document)
        )
        
        # Регистрация обработчика текстовых сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        
        logger.info("Обработчики зарегистрированы")
        logger.info("Бот запущен и готов к работе")
        
        # Запуск бота (версия 22.5 - run_polling сам управляет event loop)
        application.run_polling(drop_pending_updates=True)
        
    except ValueError as e:
        logger.error(f"Ошибка конфигурации: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания, остановка бота...")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Бот остановлен")


if __name__ == "__main__":
    main()

