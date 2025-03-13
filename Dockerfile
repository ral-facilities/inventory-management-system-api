FROM python:3.12.9-alpine3.20@sha256:4ce45e8acd11d49ee07aa736cd7ca2950df75033b946f3a5d9eca1cb4aae2ab7

WORKDIR /inventory-management-system-api-run

COPY pyproject.toml ./
COPY inventory_management_system_api/ inventory_management_system_api/

RUN --mount=type=cache,target=/root/.cache \
    set -eux; \
    \
    python3 -m pip install .;

CMD ["uvicorn", "inventory_management_system_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
EXPOSE 8000
