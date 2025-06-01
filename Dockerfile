FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -m spacy download de_core_news_sm

COPY src/ ./src/
COPY config/ ./config/

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]