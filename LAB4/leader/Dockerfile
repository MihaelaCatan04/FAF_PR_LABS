FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY leader/leader.py .

CMD ["python", "leader.py"]

HEALTHCHECK --interval=5s --timeout=2s --start-period=5s --retries=3 \
	CMD python -c "import sys,requests,os; port=os.environ.get('PORT','5000'); r=requests.get(f'http://127.0.0.1:{port}/health'); sys.exit(0 if r.status_code==200 else 1)"