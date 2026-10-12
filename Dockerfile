# ==================== Dockerfile для bothost.ru ====================
FROM python:3.11-slim

# Рабочая директория
WORKDIR /app

# Переменные окружения Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/app/data

# Системные зависимости (sqlite, ssl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Python-зависимости
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Копируем весь проект
COPY . .

# Постоянная папка для данных (bothost сохраняет её при перезапуске)
RUN mkdir -p /app/data

# Запуск бота
CMD ["python", "bot.py"]
