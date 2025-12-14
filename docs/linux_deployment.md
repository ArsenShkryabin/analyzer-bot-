# Быстрая установка бота на Linux сервер

## Требования

- Linux сервер (Ubuntu/Debian/CentOS)
- Python 3.10 или выше
- Доступ по SSH

## Шаг 1: Установка Python и зависимостей

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

# CentOS/RHEL
sudo yum install -y python3 python3-pip git
```

## Шаг 2: Клонирование проекта

```bash
# Перейдите в нужную директорию
cd /opt  # или /home/username

# Клонируйте проект
git clone https://github.com/ArsenShkryabin/analyzer-bot-.git
cd analyzer-bot-

# Или загрузите файлы через scp/sftp
```

## Шаг 3: Создание виртуального окружения

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Шаг 4: Настройка конфигурации

```bash
# Создайте файл .env
nano .env
```

Добавьте в файл:

```env
TELEGRAM_BOT_TOKEN=ваш_токен_бота
AI_API_URL=https://ваш.сервис.ai/v1/chat/completions
AI_API_KEY=ваш_ключ_api
AI_MODEL=gpt-4o
LOG_LEVEL=INFO
TEMP_FILE_PATH=./temp_files
API_TIMEOUT=180
```

Сохраните файл (Ctrl+O, Enter, Ctrl+X)

## Шаг 5: Создание директории для временных файлов

```bash
mkdir -p temp_files
chmod 755 temp_files
```

## Шаг 6: Проверка работы

```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Запустите бота
python main.py
```

Если всё работает, остановите бота (Ctrl+C).

## Шаг 7: Запуск как системный сервис (systemd)

Создайте файл сервиса:

```bash
sudo nano /etc/systemd/system/risk-analyzer-bot.service
```

Добавьте:

```ini
[Unit]
Description=Risk Analyzer Telegram Bot
After=network.target

[Service]
Type=simple
User=ваш_пользователь
WorkingDirectory=/opt/analyzer-bot-
Environment="PATH=/opt/analyzer-bot-/venv/bin"
ExecStart=/opt/analyzer-bot-/venv/bin/python /opt/analyzer-bot-/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Замените:
- `ваш_пользователь` на ваше имя пользователя (например, `ubuntu` или `root`)
- `/opt/analyzer-bot-` на путь к проекту (если клонировали в другое место)

Запустите сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl enable risk-analyzer-bot
sudo systemctl start risk-analyzer-bot
sudo systemctl status risk-analyzer-bot
```

## Альтернатива: Запуск через screen/tmux

```bash
# Установка screen
sudo apt install screen  # или yum install screen

# Создание сессии
screen -S risk_bot

# Активируйте виртуальное окружение и запустите
source venv/bin/activate
python main.py

# Отключитесь: Ctrl+A, затем D
# Вернуться: screen -r risk_bot
```

## Полезные команды

```bash
# Просмотр логов (если используется systemd)
sudo journalctl -u risk-analyzer-bot -f

# Остановка бота
sudo systemctl stop risk-analyzer-bot

# Перезапуск бота
sudo systemctl restart risk-analyzer-bot

# Проверка статуса
sudo systemctl status risk-analyzer-bot
```

## Проверка работы

1. Найдите бота в Telegram
2. Отправьте команду `/start`
3. Отправьте тестовый Excel-файл
4. Проверьте, что бот отвечает

## Решение проблем

**Бот не запускается:**
```bash
# Проверьте логи
sudo journalctl -u risk-analyzer-bot -n 50

# Проверьте .env файл
cat .env

# Проверьте права доступа
ls -la .env
```

**Ошибка с правами доступа:**
```bash
chmod 600 .env
chmod 755 temp_files
```

**Бот падает:**
- Проверьте логи
- Убедитесь, что все переменные в .env установлены
- Проверьте доступность AI API

---

**Готово!** Бот должен работать на сервере.

