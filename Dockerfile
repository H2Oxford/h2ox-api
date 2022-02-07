# syntax=docker/dockerfile:1

FROM python:slim-buster

WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

ENV PORT 8080
EXPOSE $PORT

ENTRYPOINT gunicorn app:app --bind="0.0.0.0:$PORT"
