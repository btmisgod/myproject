from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.response import error


class AppError(Exception):
    def __init__(self, message: str, *, code: str = "app_error", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error(exc.message, code=exc.code),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=error("internal server error", code="internal_error", details=str(exc)),
        )

