import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from pansen.sqla.models.main import Parent, Child


@pytest.mark.asyncio
async def test_simple_flush(sqla_session: AsyncSession):
    p = Parent()
    sqla_session.add(p)

    c = Child()
    p.children.append(c)
    await sqla_session.flush()

    assert p.id is not None
    assert c.id is not None
