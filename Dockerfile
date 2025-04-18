FROM python:3.13.3-alpine3.21@sha256:18159b2be11db91f84b8f8f655cd860f805dbd9e49a583ddaac8ab39bf4fe1a7

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
