########################################################################################################################
# Base stage, includes uv
########################################################################################################################
FROM python:3.13.13-alpine3.23@sha256:f22efe61d60550086ae899978e82929ee46458461b6251a6a16375380e9861ef AS base
COPY --from=ghcr.io/astral-sh/uv:0.10.8@sha256:88234bc9e09c2b2f6d176a3daf411419eb0370d450a08129257410de9cfafd2a /uv /uvx /bin/

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy
# Disable use of uv-managed Python versions
ENV UV_NO_MANAGED_PYTHON=1
# Disable Python downloads so that the system interpreter is used across images
ENV UV_PYTHON_DOWNLOADS=0
# Add timezone configuration - https://github.com/regebro/tzlocal/issues/70
ENV TZ=UTC

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./

########################################################################################################################
# Stage for local development
########################################################################################################################
FROM base AS dev

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    set -eux; \
    \
    # Lock and install all dependencies but do not install the project \
    uv sync --locked --no-install-project;

COPY inventory_management_system_api/ inventory_management_system_api/

RUN --mount=type=cache,target=/root/.cache/uv \
    set -eux; \
    \
    # Install the project \
    uv sync --locked;

# Ensure any installed scripts are accessible directly without uv run e.g. the `ims` CLI script
ENV PATH="/app/.venv/bin:$PATH"

CMD ["fastapi", "dev", "inventory_management_system_api/main.py", "--host", "0.0.0.0", "--port", "8000"]

EXPOSE 8000


########################################################################################################################
# Stage for running tests
########################################################################################################################
FROM dev AS test

WORKDIR /app

COPY test/ test/

CMD ["pytest",  "--config-file", "test/pytest.ini", "-v"]


########################################################################################################################
# Stage for production-ready build of the project
########################################################################################################################
FROM base AS prod-build


# Omit development dependencies
ENV UV_NO_DEV=1

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    set -eux; \
    \
    # Lock and install all dependencies but do not install the project \
    uv sync --locked --no-install-project;

COPY inventory_management_system_api/ inventory_management_system_api/

RUN --mount=type=cache,target=/root/.cache/uv \
    set -eux; \
    \
    # Install the project \
    uv sync --locked;

########################################################################################################################
# Minimal production-ready image
########################################################################################################################
# The same image that matches the build stage must be used as the path to the Python executable must be the same.
FROM python:3.13.13-alpine3.23@sha256:f22efe61d60550086ae899978e82929ee46458461b6251a6a16375380e9861ef AS prod

WORKDIR /app

RUN set -eux; \
    \
    # Create a non-root user to run as \
    addgroup -g 500 -S inventory-management-system-api; \
    adduser -S -D -G inventory-management-system-api -H -u 500 -h /app inventory-management-system-api;

# Copy the application from the prod-build stage
COPY --from=prod-build /app /app

USER inventory-management-system-api

# Ensure any installed scripts are accessible directly without uv run e.g. the `ims` CLI script
ENV PATH="/app/.venv/bin:$PATH"

CMD ["fastapi", "run", "inventory_management_system_api/main.py", "--host", "0.0.0.0", "--port", "8000"]

EXPOSE 8000
