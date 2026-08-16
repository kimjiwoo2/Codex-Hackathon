from typing import Any

from mangum import Mangum

from app.main import app


def _function_url_event(path: str = "/health") -> dict[str, Any]:
    return {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": path,
        "rawQueryString": "",
        "headers": {"host": "example.lambda-url.ap-southeast-1.on.aws"},
        "requestContext": {
            "accountId": "anonymous",
            "apiId": "example",
            "domainName": "example.lambda-url.ap-southeast-1.on.aws",
            "domainPrefix": "example",
            "http": {
                "method": "GET",
                "path": path,
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "pytest",
            },
            "requestId": "lambda-handler-test",
            "routeKey": "$default",
            "stage": "$default",
            "time": "16/Aug/2026:00:00:00 +0000",
            "timeEpoch": 1_787_011_200_000,
        },
        "isBase64Encoded": False,
    }


def test_lambda_handler_wraps_application() -> None:
    from app.lambda_handler import handler

    assert isinstance(handler, Mangum)
    assert handler.app is app


def test_function_url_health_request() -> None:
    from app.lambda_handler import handler

    response = handler(_function_url_event(), {})

    assert response["statusCode"] == 200
    assert response["headers"]["content-type"] == "application/json"
    assert response["body"] == '{"status":"ok"}'
