import logging
import datetime
from typing import Annotated, AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from fastapi import Depends
from postmarker.core import PostmarkClient
from deployment_server.config import config


logger = logging.getLogger(config.name)
logger.setLevel(logging.DEBUG if config.debug else logging.INFO)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(stream_handler)


postmark = PostmarkClient(server_token=config.postmark_server_token)


engine = create_async_engine(config.pg_conn_str)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_timestamp_for_db():
    return datetime.datetime.now(datetime.timezone.utc)
