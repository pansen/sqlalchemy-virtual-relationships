from __future__ import annotations

from sqlalchemy import Column, text, ForeignKey, DateTime, select, func, desc, and_, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, aliased, foreign

from pansen.sqla.models.meta import Base


class Parent(Base):
    __tablename__ = "parent"
    # Read `id` on flush
    # https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html#preventing-implicit-io-when-using-asyncsession
    __mapper_args__ = {"eager_defaults": True}

    id = Column(UUID, primary_key=True, unique=True, server_default=text("uuid_generate_v1()"))
    # https://docs.sqlalchemy.org/en/14/orm/basic_relationships.html#many-to-many
    children = relationship(
        'Child',
        order_by="desc(Child.created_at)",
        uselist=True,
        # https://docs.sqlalchemy.org/en/14/orm/relationship_api.html#sqlalchemy.orm.relationship.params.back_populates
        back_populates='parent',
        cascade="save-update, merge, delete, delete-orphan"
    )  # type: List[Child]
    # Write-only relationship
    children_writes = relationship(
        'Child',
        order_by="desc(Child.created_at)",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="noload",
    )
    created_at = Column('created_at', DateTime(timezone=True), server_default=text("now()"),
                        nullable=False)


class Child(Base):
    __tablename__ = "child"
    __mapper_args__ = {"eager_defaults": True}
    id = Column(UUID, primary_key=True, unique=True, server_default=text("uuid_generate_v1()"))
    txt = Column(String, nullable=True)
    parent_id = Column(UUID, ForeignKey("parent.id"), primary_key=True)
    parent = relationship('Parent', back_populates='children', )
    created_at = Column('created_at', DateTime(timezone=True), server_default=text("now()"),
                        nullable=False)


# magic without views
# -------------------
# see:
# - https://docs.sqlalchemy.org/en/14/orm/join_conditions.html#row-limited-relationships-with-window-functions
# - https://docs.sqlalchemy.org/en/14/orm/join_conditions.html#composite-secondary-joins

CHILDREN_CAPPED_COUNT = 2

ChildPartition = select(
    Child,
    func.row_number().over(order_by=desc(Child.created_at),
                           partition_by=Child.parent_id).label("index"),
) \
    .alias()

ChildPartitioned = aliased(Child, ChildPartition)

Parent.children_capped = relationship(
    ChildPartitioned,
    primaryjoin=lambda: and_(
        # Ensure that only those columns referring to a parent column are marked as foreign, either via the foreign() annotation or via the foreign_keys argument.
        foreign(ChildPartitioned.parent_id) == Parent.id,
        ChildPartition.c.index <= CHILDREN_CAPPED_COUNT,
    ),
    # https://docs.sqlalchemy.org/en/14/orm/relationship_api.html#sqlalchemy.orm.relationship.params.foreign_keys
    foreign_keys=[Child.parent_id, ],
    uselist=True
)
