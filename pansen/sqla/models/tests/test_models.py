import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from pansen.sqla.models.main import Parent, Child, CHILDREN_CAPPED_COUNT


@pytest.mark.asyncio
async def test_simple_flush(sqla_session: AsyncSession):
    p = Parent()
    sqla_session.add(p)

    c = Child()
    p.children.append(c)
    await sqla_session.flush()

    assert p.id is not None
    assert c.id is not None


@pytest.mark.asyncio
async def test_select_in_load(sqla_session: AsyncSession, parent_with_children):
    await sqla_session.flush()
    parent_id = parent_with_children.id
    assert parent_id

    s_ = select(Parent)
    s_ = s_.options(
        selectinload(Parent.children),
        selectinload(Parent.children_capped),
    )
    s_ = s_.filter(Parent.id == parent_id)
    parent_loaded: Parent = (await sqla_session.execute(s_)) \
        .scalars().one()

    assert len(parent_loaded.children) == len(parent_with_children.children)
    assert len(parent_loaded.children_capped) == CHILDREN_CAPPED_COUNT


@pytest.fixture()
def parent_with_children(sqla_session: AsyncSession) -> Parent:
    p = Parent()
    for i in range(0, 10):
        c = Child()
        p.children.append(c)
    sqla_session.add(p)
    return p
