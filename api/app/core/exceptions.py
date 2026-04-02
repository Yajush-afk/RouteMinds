from fastapi import Request
from fastapi.responses import JSONResponse


class RouteMindsException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ModelNotLoadedException(RouteMindsException):
    def __init__(self):
        super().__init__(
            message="ML model is not loaded. Predictions are unavailable.",
            status_code=503,
        )

class ModelArtifactMissingException(RouteMindsException):
    def __init__(self, artifact_name: str, artifact_path: str):
        super().__init__(
            message=(
                f"Required {artifact_name} artifact is unavailable at "
                f"'{artifact_path}'."
            ),
            status_code=503,
        )


class PredictionRequestException(RouteMindsException):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=400)


class GTFSStaticDataException(RouteMindsException):
    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message=message, status_code=status_code)


class RouteNotFoundException(RouteMindsException):
    def __init__(self, source: str, destination: str):
        super().__init__(
            message=f"No route found between '{source}' and '{destination}'.",
            status_code=404,
        )

class StopNotFoundException(RouteMindsException):
    def __init__(self, stop_id: str):
        super().__init__(
            message=f"Stop '{stop_id}' not found.",
            status_code=404,
        )

async def routeminds_exception_handler(
    request: Request, exc: RouteMindsException
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )
