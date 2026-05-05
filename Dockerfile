FROM python:3.12-alpine
LABEL authors="Karla Schramm"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /makeascene-backend

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .
RUN chmod +x ./docker-entrypoint.sh

CMD ["./docker-entrypoint.sh"]