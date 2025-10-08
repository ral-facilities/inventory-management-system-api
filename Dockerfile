FROM python:3.13.8-alpine3.22@sha256:24e4e48dffe56280cf8c873070e2238561f95d2f99b121f64475cceb831ed50a AS base

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
