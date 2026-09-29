from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.api.responses import error_response


def _json_safe_validation_errors(errors: list[dict]) -> list[dict]:
    safe_errors = []
    for error in errors:
        safe_error = dict(error)
        if "ctx" in safe_error and isinstance(safe_error["ctx"], dict):
            safe_error["ctx"] = {
                key: str(value) for key, value in safe_error["ctx"].items()
            }
        safe_errors.append(safe_error)
    return safe_errors


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response("http_error", str(exc.detail)),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_response(
                "validation_error",
                "Request validation failed.",
                details=_json_safe_validation_errors(exc.errors()),
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=error_response(
                "internal_server_error",
                "An unexpected server error occurred.",
            ),
        )
