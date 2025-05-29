FROM python:3.12.10-alpine3.21@sha256:9c51ecce261773a684c8345b2d4673700055c513b4d54bc0719337d3e4ee552e AS base

WORKDIR /app

COPY pyproject.toml requirements.txt ./
COPY inventory_management_system_api/ inventory_management_system_api/


FROM base AS dev

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache \
    set -eux; \
    \
    # Ensure the package and the project scripts get installed properly using the pyproject.toml file \
    pip install --no-cache-dir .[dev]; \
    # Ensure the pinned versions of the production dependencies and subdependencies are installed \
    pip install --no-cache-dir --requirement requirements.txt;

CMD ["fastapi", "dev", "inventory_management_system_api/main.py", "--host", "0.0.0.0", "--port", "8000"]

EXPOSE 8000


FROM dev AS test

WORKDIR /app

COPY test/ test/

CMD ["pytest",  "--config-file", "test/pytest.ini", "-v"]


FROM base AS prod

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache \
    set -eux; \
    \
    # Ensure the package and the project scripts get installed properly using the pyproject.toml file \
    pip install --no-cache-dir .; \
    # Ensure the pinned versions of the production dependencies and subdependencies are installed \
    pip install --no-cache-dir --requirement requirements.txt; \
    \
    # Create a non-root user to run as \
    addgroup -g 500 -S inventory-management-system-api; \
    adduser -S -D -G inventory-management-system-api -H -u 500 -h /app inventory-management-system-api;

USER inventory-management-system-api

CMD ["fastapi", "run", "inventory_management_system_api/main.py", "--host", "0.0.0.0", "--port", "8000"]

EXPOSE 8000
