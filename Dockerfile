FROM python:3.12-slim AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --upgrade pip && /opt/venv/bin/pip install -r requirements.txt

FROM python:3.12-slim AS runtime
ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd --system smarthealth && useradd --system --gid smarthealth --home /app smarthealth
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=smarthealth:smarthealth . .
RUN mkdir -p /var/lib/smarthealth/private_uploads && chown -R smarthealth:smarthealth /var/lib/smarthealth /app
USER smarthealth
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3)"
ENTRYPOINT ["/app/deploy/entrypoint.sh"]
CMD ["gunicorn", "--config", "deploy/gunicorn.conf.py", "app:app"]
