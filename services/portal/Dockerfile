# Portal image — self-contained build from the arca-platform repo.
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi>=0.110 \
    "uvicorn[standard]>=0.29" \
    httpx>=0.27 \
    itsdangerous>=2.1 \
    jinja2>=3.1 \
    "PyJWT[crypto]>=2.8" \
    redis>=5.0

COPY services/portal/src /app/portal

EXPOSE 8000
CMD ["uvicorn", "portal.main:app", "--host", "0.0.0.0", "--port", "8000"]
