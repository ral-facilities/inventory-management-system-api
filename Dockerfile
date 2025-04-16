FROM python:3.12.10-alpine3.21@sha256:e5956ba054e89858c706f038a980241ea38565176619f1a2695cb9b039ea1265

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
