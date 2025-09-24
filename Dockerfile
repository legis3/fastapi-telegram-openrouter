FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# системные зависимости по минимуму (при желании добавь tzdata, curl и т.п.)
RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# копируем только приложение
COPY app ./app

EXPOSE 8000
# Один воркер, т.к. внутри процесса ещё и aiogram long-polling (если USE_WEBHOOK=false).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]