FROM python:3.11-slim AS builder

WORKDIR /install

COPY requirements.docker.txt .

RUN pip install --no-cache-dir --prefix=/install/deps -r requirements.docker.txt

FROM python:3.11-slim AS runtime

WORKDIR /app

COPY --from=builder /install/deps /usr/local

COPY app/ ./app/

RUN mkdir -p /app/temp_data

RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
