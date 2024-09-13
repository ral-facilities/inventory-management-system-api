FROM python:3.12.5-alpine3.20@sha256:bb5d0ac04679d78a1258e7dfacdb4d9bdefe9a10480eaf9b4bb09445d076369f

WORKDIR /inventory-management-system-api-run

# Requirement when using a different workdir to get scripts to import correctly
ENV PYTHONPATH="${PYTHONPATH}:/inventory-management-system-api-run"

COPY pyproject.toml ./
COPY inventory_management_system_api/ inventory_management_system_api/

RUN --mount=type=cache,target=/root/.cache \
    set -eux; \
    \
    python3 -m pip install .;

CMD ["uvicorn", "inventory_management_system_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
EXPOSE 8000
