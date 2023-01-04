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
async def test_select_in_load(sqla_session: AsyncSession, parent_with_children: Parent):
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


@pytest.mark.asyncio
async def test_write_to_capped(sqla_session: AsyncSession, parent_with_children: Parent):
    child_count = len(parent_with_children.children)
    await sqla_session.flush()
    parent_id = parent_with_children.id
    assert parent_id

    s_ = select(Parent)
    s_ = s_.options(
        selectinload(Parent.children_capped),
        # We do not want to load the whole `children` list as this is too expensive
        # selectinload(Parent.children),
    )
    s_ = s_.filter(Parent.id == parent_id)
    parent_loaded: Parent = (await sqla_session.execute(s_)) \
        .scalars().one()

    assert len(parent_loaded.children_capped) == CHILDREN_CAPPED_COUNT
    child = Child()
    # This is important to for the write-only relation to have the child attached to the parents relation.
    child.parent = parent_with_children
    parent_loaded.children_writes.append(child)
    await sqla_session.flush()
    assert child.id is not None

    child_loaded: Child = (await sqla_session.execute(select(Child).filter(Child.id == child.id))) \
        .scalars().one()
    assert child_loaded.id == child.id

    # Load again to see if our addition worked.
    parent_loaded2: Parent = (await sqla_session.execute(s_)) \
        .scalars().one()
    assert len(parent_loaded2.children) > child_count
    assert child.id in [c.id for c in parent_loaded2.children]

@pytest.fixture()
def parent_with_children(sqla_session: AsyncSession) -> Parent:
    p = Parent()
    for i in range(0, 10):
        c = Child()
        p.children.append(c)
    sqla_session.add(p)
    return p
