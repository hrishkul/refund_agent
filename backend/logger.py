import sys
import uuid
from contextvars import ContextVar
from os import getenv

from loguru import logger


request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


def setup_logger() -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        serialize=True,
        level=getenv("LOG_LEVEL", "INFO"),
        enqueue=True,
        backtrace=False,
        diagnose=False,
    )


def new_request_id() -> str:
    return str(uuid.uuid4())


def set_request_id(request_id: str) -> None:
    request_id_ctx.set(request_id)


def log_decision(**fields) -> None:
    logger.bind(request_id=request_id_ctx.get(), **fields).info("agent_decision")
