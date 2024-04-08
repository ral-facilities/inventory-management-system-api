FROM python:3.12.2-alpine3.19@sha256:c7eb5c92b7933fe52f224a91a1ced27b91840ac9c69c58bef40d602156bcdb41

WORKDIR /inventory-management-system-api-run

COPY pyproject.toml ./
COPY inventory_management_system_api/ inventory_management_system_api/

RUN --mount=type=cache,target=/root/.cache \
    set -eux; \
    \
    python3 -m pip install .;

CMD ["uvicorn", "inventory_management_system_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
EXPOSE 8000
