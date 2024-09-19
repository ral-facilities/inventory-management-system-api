FROM python:3.12.6-alpine3.20@sha256:7130f75b1bb16c7c5d802782131b4024fe3d7a87ce7d936e8948c2d2e0180bc4

WORKDIR /inventory-management-system-api-run

COPY pyproject.toml ./
COPY inventory_management_system_api/ inventory_management_system_api/

RUN --mount=type=cache,target=/root/.cache \
    set -eux; \
    \
    python3 -m pip install .;

CMD ["fastapi", "dev", "inventory_management_system_api/main.py", "--host", "0.0.0.0", "--port", "8000"]
EXPOSE 8000
