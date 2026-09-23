class AppError(Exception):
    """Rendered as {"error": {"code", "message"}}. Codes are stable; the frontend maps them to Hebrew."""

    def __init__(self, status: int, code: str, message: str = ""):
        super().__init__(message or code)
        self.status, self.code, self.message = status, code, message or code


def not_found() -> AppError:
    return AppError(404, "not_found")


def forbidden() -> AppError:
    return AppError(403, "forbidden")
