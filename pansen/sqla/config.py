import logging
import os
from datetime import tzinfo
from logging.config import dictConfig
from urllib import parse

import pytz
from pydantic import BaseSettings, validator
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from pansen.sqla import PROJECT_ROOT

log = logging.getLogger(__name__)


class Config(BaseSettings):
    DEBUG: bool = False
    LOGGING_FORMAT_JSON: bool = False
    TEST_MODE: bool = False

    POSTGRES_URL: str
    SQLA_URL: str | None
    POSTGRES_CONNECTION_ARGS: dict | None

    ENV: str = 'dev'
    TZ: tzinfo

    VERSION_COMMIT_HASH: str | None
    VERSION: str | None

    @validator('TZ', pre=True)
    def convert_to_tzinfo(cls, value):
        return pytz.timezone(value)

    class Config:
        # https://pydantic-docs.helpmanual.io/usage/settings/#dotenv-env-support
        env_file= os.path.join(PROJECT_ROOT, '.env')
        env_file_encoding = 'utf-8'


def configure() -> Config:
    """
    Parse the ENV and prepare a `Config` instance according to that.
    """
    c = Config()

    # asyncpg connection string
    parsed = parse.urlparse(c.POSTGRES_URL)
    # create a kw_args dict, which fits https://github.com/MagicStack/asyncpg#basic-usage
    c.POSTGRES_CONNECTION_ARGS = {
        "user": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname,
        "port": str(parsed.port),
        "database": parsed.path.lstrip("/"),  # type: ignore
    }
    # sqlalchemy connection string
    c.SQLA_URL = f"postgresql+asyncpg://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}/{c.POSTGRES_CONNECTION_ARGS['database']}"

    dictConfig(log_config(level=c.DEBUG and 'DEBUG' or 'INFO',
                          enable_json_format=c.LOGGING_FORMAT_JSON))

    return c


def log_config(level='INFO', enable_json_format=False, ):
    lconf = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s %(levelname)-5.5s [%(name)s][%(threadName)s] %(message)s"
            },
            "json": {
                "format": "%(levelname)-5.5s %(message)s %(name)s %(threadName)s",
                "class": "pythonjsonlogger.jsonlogger.JsonFormatter"
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": enable_json_format and 'json' or 'standard',
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            # All child loggers of that module logger will propagate up to its parent logger
            # (this `gdd` logger)
            # https://docs.python.org/3/howto/logging.html#loggers
            "pansen": {
                "level": level,
                "propagate": False,
                "handlers": ["console", ],
            },
            # Skip useless error messages
            # https://github.com/encode/uvicorn/issues/562
            "uvicorn.error": {
                "level": level,
                "propagate": False,
                "handlers": [],
            },
        },
        "root": {
            "level": level,
            # Don't apply `smtp_handler` here, otherwise we'll also receive mails from the
            # websocket connectors. Which is not what we want.
            "handlers": ["console", ],
        },
    }

    return lconf


def sqla_engine(config: Config) -> AsyncEngine:
    """
    Deprecated, use `SQLAlchemyEnginePerLoop`
    """
    sqla_engine = create_async_engine(
        config.SQLA_URL,
        echo=False,
        connect_args={
            # We set this, as there is a bug in asyncpg or postgres - dunno.
            # Anyway we don't want to turn of the JIT globally in postgres.
            'server_settings': {
                'jit': 'off'
            }
        }
    )
    log.debug("got an sqla_engine: %s ...", sqla_engine)
    return sqla_engine
