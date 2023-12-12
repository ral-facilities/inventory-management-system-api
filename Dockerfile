FROM python:3.10-alpine3.17

WORKDIR /inventory-management-system-api-run

COPY pyproject.toml ./
COPY inventory_management_system_api/ inventory_management_system_api/

RUN --mount=type=cache,target=/root/.cache \
    set -eux; \
    \
    python3 -m pip install .;

ENV API__TITLE="Inventory Management System API"
ENV API__DESCRIPTION="This is the API for the Inventory Management System"
ENV API__ROOT_PATH=""
ENV DATABASE__PROTOCOL=mongodb
ENV DATABASE__USERNAME=root
ENV DATABASE__PASSWORD=example
ENV DATABASE__HOSTNAME=localhost
ENV DATABASE__PORT=27017
ENV DATABASE__NAME=ims

CMD ["uvicorn", "inventory_management_system_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
EXPOSE 8000
