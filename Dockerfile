FROM python:3.12.9-alpine3.21@sha256:28b8a72c4e0704dd2048b79830e692e94ac2d43d30c914d54def6abf74448a4e

WORKDIR /inventory-management-system-api-run

COPY pyproject.toml requirements.txt ./
COPY inventory_management_system_api/ inventory_management_system_api/

RUN --mount=type=cache,target=/root/.cache \
    set -eux; \
    \
    python -m pip install .[dev]; \
    # Ensure the pinned versions of the production dependencies and subdependencies are installed \
    python -m pip install --no-cache-dir --requirement requirements.txt;

CMD ["uvicorn", "inventory_management_system_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
EXPOSE 8000
