FROM python:3.12.4-alpine3.20@sha256:0bd77ae937dce9037e136ab35f41eaf9e012cfd741fc3c8dd4b3e2b63499f12c

WORKDIR /inventory-management-system-api-run

COPY pyproject.toml ./
COPY inventory_management_system_api/ inventory_management_system_api/

RUN --mount=type=cache,target=/root/.cache \
    set -eux; \
    \
    python3 -m pip install .;

CMD ["uvicorn", "inventory_management_system_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
EXPOSE 8000
