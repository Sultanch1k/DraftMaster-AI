# DraftMaster AI API image — two-stage build keeps the runtime layer small.
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt ./
COPY services/engine ./services/engine
COPY services/api/requirements.txt ./services/api/requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/services/engine" \
    DRAFTMASTER_ENVIRONMENT=production

RUN useradd --create-home --uid 10001 app
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY services/api ./services/api
COPY services/engine ./services/engine
COPY data/artifacts ./data/artifacts

# Normalise permissions: the non-root runtime user must be able to read the
# application code and the artifacts regardless of the host checkout's mode.
RUN chmod -R a+rX /app && chmod -R a+rX /opt/venv

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

WORKDIR /app/services/api
CMD ["uvicorn", "draftmaster_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
