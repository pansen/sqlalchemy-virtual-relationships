from __future__ import annotations

from sqlalchemy import Column, text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from pansen.sqla.models.meta import Base


class Parent(Base):
    __tablename__ = "parent"
    # Read `id` on flush
    # https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html#preventing-implicit-io-when-using-asyncsession
    __mapper_args__ = {"eager_defaults": True}

    id = Column(UUID, primary_key=True, unique=True, server_default=text("uuid_generate_v1()"))
    # https://docs.sqlalchemy.org/en/14/orm/basic_relationships.html#many-to-many
    children = relationship('Child',
                            order_by="desc(Child.created_at)",
                            uselist=True,
                            # https://docs.sqlalchemy.org/en/14/orm/relationship_api.html#sqlalchemy.orm.relationship.params.back_populates
                            back_populates='parent',
                            cascade="save-update, merge, delete, delete-orphan"
                            )  # type: List[Child]
    created_at = Column('created_at', DateTime(timezone=True), server_default=text("now()"),
                        nullable=False)


class Child(Base):
    __tablename__ = "child"
    __mapper_args__ = {"eager_defaults": True}
    id = Column(UUID, primary_key=True, unique=True, server_default=text("uuid_generate_v1()"))
    parent_id = Column(UUID, ForeignKey("parent.id"), primary_key=True)
    parent = relationship('Parent', back_populates='children', )
    created_at = Column('created_at', DateTime(timezone=True), server_default=text("now()"),
                        nullable=False)
