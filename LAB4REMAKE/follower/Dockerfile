FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY follower /app/follower

ENV PYTHONPATH=/app
CMD ["uvicorn", "follower.main:app", "--host", "0.0.0.0", "--port", "5000"]
