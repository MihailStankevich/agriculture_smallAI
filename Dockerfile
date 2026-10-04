FROM python:3.12-slim
WORKDIR /app
COPY . .
ENV HOST=0.0.0.0
CMD ["python", "server.py"]
