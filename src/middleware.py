"""Request logging middleware that adds a unique ID to each response."""

import logging
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse


logger = logging.getLogger(__name__)


async def log_requests(request: Request, call_next):
    """Log one request and attach its request ID to the response."""
    # Create an ID that can connect a client response with its log messages.
    request_id = uuid.uuid4().hex[:8]
    request.state.request_id = request_id

    # Start measuring time before the request reaches its endpoint.
    started = time.perf_counter()

    try:
        # Let FastAPI handle the request and produce its response.
        response = await call_next(request)
    except Exception:
        # Record the traceback for debugging without exposing it to the client.
        logger.error("Unexpected request error: request_id=%s", request_id, exc_info=True)
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # Calculate total time spent handling this request in milliseconds.
    duration_ms = (time.perf_counter() - started) * 1000
    message = (
        "Request: request_id=%s method=%s path=%s status_code=%s duration_ms=%.2f"
    )
    details = (
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    # Use stronger log levels for client errors and server errors.
    if response.status_code >= 500:
        logger.error(message, *details)
    elif response.status_code >= 400:
        logger.warning(message, *details)
    else:
        logger.info(message, *details)

    # Return the request ID so clients can report it when asking for help.
    response.headers["X-Request-ID"] = request_id
    return response