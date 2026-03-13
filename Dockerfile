FROM python:3.11-slim

WORKDIR /app

# Instala dependências da aplicação
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY app ./app
COPY main.py .

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]

