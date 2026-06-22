"""Provides some structured exceptions and FastAPI error handlers for them"""

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jose import ExpiredSignatureError, JWTError
from starlette.exceptions import HTTPException

from rungoal.cors import allowed_origins
from rungoal.models import Error
import traceback

class RecordNotFoundError(LookupError):
    """Represents a failure to find a database record"""

    def __init__(self, params):
        self.params = params


class ConflictError(Exception):
    """Represents a database conflict"""

    def __init__(self, params):
        self.params = params


def init_exception_handlers(app: FastAPI):
    def wrap_error_response(
        request: Request, status_code: int, error: Error, headers=None
    ) -> JSONResponse:
        # Ensure the header normally added to the response by the CORS middleware is included,
        # otherwise the browser will fixate on it
        origin = request.headers.get("origin")
        cors_header = {
            "Access-Control-Allow-Origin": origin
            if origin in allowed_origins
            else allowed_origins[0]
        }

        return JSONResponse(
            status_code=status_code,
            headers=(headers | cors_header) if headers else cors_header,
            content=jsonable_encoder(error),
        )

    @app.exception_handler(RecordNotFoundError)
    def on_record_not_found(request: Request, _exc: RecordNotFoundError):
        return wrap_error_response(
            request, status.HTTP_404_NOT_FOUND, Error(title="Record not found")
        )

    @app.exception_handler(ExpiredSignatureError)
    def on_expired_signature(request: Request, exc: ExpiredSignatureError):
        return wrap_error_response(
            request,
            status.HTTP_401_UNAUTHORIZED,
            Error(title="Authentication credentials expired", detail=str(exc)),
        )

    @app.exception_handler(JWTError)
    def on_token_error(request: Request, exc: JWTError):
        return wrap_error_response(request, status.HTTP_401_UNAUTHORIZED, Error(title=str(exc)))

    @app.exception_handler(RequestValidationError)
    def on_validation_exception(request: Request, exc: RequestValidationError):
        return wrap_error_response(
            request,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            Error(title="Validation error", detail=str(exc)),
        )

    @app.exception_handler(HTTPException)
    def on_http_exception(request, exc: HTTPException):
        return wrap_error_response(request, exc.status_code, Error(title=exc.detail), exc.headers)

    @app.exception_handler(Exception)
    def on_exception(request: Request, exc: Exception):
        traceback.print_exception(exc)
        return wrap_error_response(
            request,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            Error(title="Something went wrong...", detail=str(exc)),
        )
