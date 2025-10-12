FROM python:3.11-slim

WORKDIR /app

COPY . .

EXPOSE 8080

ENTRYPOINT ["python", "main.py"]
CMD ["./my_website", "8080"]