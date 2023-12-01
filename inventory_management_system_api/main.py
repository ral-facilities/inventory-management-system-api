"""
Main module contains the API entrypoint.
"""
import logging

from fastapi import FastAPI, Request, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from inventory_management_system_api.core.config import config
from inventory_management_system_api.core.logger_setup import setup_logger
from inventory_management_system_api.routers.v1 import catalogue_category, catalogue_item, system, manufacturer

app = FastAPI(title=config.api.title, description=config.api.description, root_path=config.api.root_path)

setup_logger()
logger = logging.getLogger()
logger.info("Logging now setup")


@app.exception_handler(Exception)
async def custom_general_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """
    Custom exception handler for FastAPI to handle uncaught exceptions. It logs the error and returns an appropriate
    response.

    :param _: Unused
    :param exc: The exception object that triggered this handler.
    :return: A JSON response indicating that something went wrong.
    """
    logger.exception(exc)
    return JSONResponse(content={"detail": "Something went wrong"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Custom exception handler for FastAPI to handle `RequestValidationError`.

    This method is used to handle validation errors that occur when processing incoming requests in FastAPI. When a
    `RequestValidationError` is raised during request parsing or validation, this handler will be triggered to log the
    error and call `request_validation_exception_handler` to return an appropriate response.

    :param request: The incoming HTTP request that caused the validation error.
    :param exc: The exception object representing the validation error.
    :return: A JSON response with validation error details.
    """
    logger.exception(exc)
    return await request_validation_exception_handler(request, exc)


# Fixes CORS issues but should be updated before deploying to prod
ALLOWED_ORIGINS = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalogue_category.router)
app.include_router(catalogue_item.router)
app.include_router(manufacturer.router)
app.include_router(system.router)


@app.get("/")
def read_root():
    """
    Root endpoint for the API.
    """
    return {"Title": "Inventory Management System API"}
