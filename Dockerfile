FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Run as an unprivileged user. The scan database folder must be writable by this UID;
# with docker-compose that means on the host: sudo chown -R 10001:10001 /srv/revolt-data
RUN useradd --system --uid 10001 --no-create-home revolt
USER revolt
EXPOSE 8502
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8502", "--log-level", "info", "--use-colors"]
