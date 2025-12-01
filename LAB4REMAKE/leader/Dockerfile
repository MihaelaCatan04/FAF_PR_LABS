FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY leader /app/leader

ENV PORT=5000
ENV PYTHONPATH=/app
CMD ["uvicorn", "leader.main:app", "--host", "0.0.0.0", "--port", "5000"]
