FROM python:3.12.10-alpine3.21@sha256:c08bfdbffc9184cdfd225497bac12b2c0dac1d24bbe13287cfb7d99f1116cf43

WORKDIR /inventory-management-system-api-run

# Requirement when using a different workdir to get scripts to import correctly
ENV PYTHONPATH="${PYTHONPATH}:/inventory-management-system-api-run"

COPY pyproject.toml requirements.txt ./
COPY inventory_management_system_api/ inventory_management_system_api/

RUN --mount=type=cache,target=/root/.cache \
    set -eux; \
    \
    python -m pip install .[dev]; \
    # Ensure the pinned versions of the production dependencies and subdependencies are installed \
    python -m pip install --no-cache-dir --requirement requirements.txt;

CMD ["fastapi", "dev", "inventory_management_system_api/main.py", "--host", "0.0.0.0", "--port", "8000"]
EXPOSE 8000
