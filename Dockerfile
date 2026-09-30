FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py logo.pn[g] ./
EXPOSE 8501
CMD ["uvicorn main:app", "run", "revolt_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
