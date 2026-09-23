# Validators image — self-contained build from the arca-platform repo.
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    "fastapi>=0.110" \
    "uvicorn[standard]>=0.29" \
    "rdflib>=7" \
    "pyshacl>=0.25" \
    "PyJWT[crypto]>=2.8" \
    "pyyaml>=6.0" \
    "httpx>=0.27"

COPY services/validators/src /app/validators
COPY services/validators/shapes /app/shapes

EXPOSE 8000
CMD ["uvicorn", "validators.main:app", "--host", "0.0.0.0", "--port", "8000"]
