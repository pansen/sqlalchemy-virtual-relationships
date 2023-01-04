import warnings

import pytest_asyncio
from sqlalchemy import create_engine, text

from pansen.sqla.config import Config, configure
from pansen.sqla.models import AsyncSessionMaker
from pansen.sqla.models.meta import metadata

warnings.filterwarnings("error")
import logging
from unittest import mock

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

log = logging.getLogger(__name__)


@pytest_asyncio.fixture()  # type: ignore
async def _sqla_engine(config: Config, db_schema_migrations, event_loop) -> AsyncEngine:
    from pansen.sqla.config import sqla_engine
    sqla_engine = sqla_engine(config)

    log.info("got an sqla_engine: %s ...", sqla_engine)
    try:
        yield sqla_engine
    finally:
        await sqla_engine.dispose()


@pytest_asyncio.fixture()  # type: ignore
async def sqla_session(_sqla_engine) -> AsyncSession:
    # expire_on_commit=False will prevent attributes from being expired
    # after commit.
    AsyncSessionMaker.configure(bind=_sqla_engine)
    async with AsyncSessionMaker(expire_on_commit=False) as session:  # type: AsyncSession
        def dummy_commit():
            log.warning('Skipped commit')
            pass

        with mock.patch.object(session, "commit", side_effect=dummy_commit):  # noqa F841
            # To avoid calling `close` in FastApi, we set a marker here.
            session.info['is_test'] = True
            yield session

        await session.rollback()

        # Here we do manually, what seems buggy in `sqlalchemy.orm.scoping.scoped_session.remove`.
        # As a result, we can safely suppress the resulting warning.
        # ** patch: start
        if AsyncSessionMaker.registry.has():
            await AsyncSessionMaker.registry().close()
        # ** patch: end
        await AsyncSessionMaker.remove()


@pytest.fixture()
def _config() -> Config:
    c = configure()
    c.TEST_MODE = True

    return c


@pytest_asyncio.fixture()
def config(_config: Config, event_loop) -> Config:
    """
    Fixture to possibly depend on other fixtures

    We try to depend on `event_loop` as early as possible to avoid weird errors. May
    be useless.

    Via: https://github.com/pytest-dev/pytest-asyncio/issues/38#issuecomment-264415067
    """
    if not _config.POSTGRES_URL.endswith('_test'):
        _config.POSTGRES_URL = _config.POSTGRES_URL + '_test'

    yield _config


@pytest.fixture(scope="module")
def db_schema_migrations(request, _sync_sqla_engine):
    with _sync_sqla_engine.begin() as conn:
        conn.execute(
            text(
                'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
            ))
        metadata.bind = _sync_sqla_engine
        metadata.drop_all()
        metadata.create_all(conn)


@pytest.fixture(scope="module")
def _sync_sqla_engine():
    # HACK this is a copy
    config = configure()

    sqla_engine = create_engine(
        # Don't use `config.SQLA_URL` here, as we're not in async mode.
        config.POSTGRES_URL,
        echo=False,
    )

    yield sqla_engine
