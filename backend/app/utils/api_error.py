from fastapi import HTTPException


def error_detail(error_code: str, **kwargs):
    return {"error_code": error_code, **kwargs}


def raise_api_error(status_code: int, error_code: str, **kwargs):
    raise HTTPException(status_code=status_code, detail=error_detail(error_code, **kwargs))
