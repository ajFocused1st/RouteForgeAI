from typing import Any


def success_response(data: Any) -> dict[str, Any]:
    return {
        "ok": True,
        "data": data,
        "error": None,
    }


def error_response(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {
        "ok": False,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
    }
