from typing import cast

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.types import ExceptionHandler

from app.core.errors import AppError
from app.schemas.common import ErrorDetail, ErrorResponse


def _response(*, status_code: int, code: str, message: str) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


async def app_error_handler(_request: Request, error: AppError) -> JSONResponse:
    return _response(status_code=error.status_code, code=error.code, message=error.message)


async def http_error_handler(_request: Request, error: HTTPException) -> JSONResponse:
    code = "HTTP_ERROR"
    message = str(error.detail)
    if isinstance(error.detail, dict):
        code = str(error.detail.get("code", code))
        message = str(error.detail.get("message", message))
    return _response(status_code=error.status_code, code=code, message=message)


async def validation_error_handler(
    _request: Request,
    _error: RequestValidationError,
) -> JSONResponse:
    return _response(
        status_code=422,
        code="VALIDATION_ERROR",
        message="요청 형식이 올바르지 않습니다.",
    )


async def unexpected_error_handler(_request: Request, _error: Exception) -> JSONResponse:
    return _response(
        status_code=500,
        code="INTERNAL_SERVER_ERROR",
        message="서버에서 요청을 처리하지 못했습니다.",
    )


def register_error_handlers(app: FastAPI) -> None:
    """Install the common envelope without coupling feature routers to handlers."""
    handlers = (
        (AppError, app_error_handler),
        (HTTPException, http_error_handler),
        (RequestValidationError, validation_error_handler),
        (Exception, unexpected_error_handler),
    )
    for exception_type, handler in handlers:
        app.add_exception_handler(exception_type, cast(ExceptionHandler, handler))
