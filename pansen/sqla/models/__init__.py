from asyncio import current_task

from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session
from sqlalchemy.orm import sessionmaker

async_session_factory = sessionmaker(class_=AsyncSession)
AsyncSessionMaker = async_scoped_session(async_session_factory, scopefunc=current_task)

