# Arca Platform — shared runtime foundation
# Multi-stage build for the platform services.

FROM python:3.12-slim AS builder
WORKDIR /build
RUN pip install --no-cache-dir hatch
COPY pyproject.toml .
RUN mkdir -p sdk adapters schemas services tests contracts && \
    python -m hatch build -t wheel && ls dist/

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl[services,messaging,observability,tests]
COPY . /app
EXPOSE 8000
CMD ["uvicorn", "services.bootstrap.src.main:app", "--host", "0.0.0.0", "--port", "8000"]
