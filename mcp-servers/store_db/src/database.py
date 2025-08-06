import os

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# DATABASE_URL = "postgresql+asyncpg://user:password@host:port/database"
# For mcp_dbstore, ensure this DATABASE_URL is appropriate for its deployment
# context. It might be the same as appserver, or different if it connects to a
# different DB instance or with different credentials.
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://myuser:mypassword@127.0.0.1:5432/store_db"
)

engine = create_async_engine(DATABASE_URL, echo=False)  # echo=True for debugging SQL

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


# SQLAlchemy models (defined here for self-containment, could also be in a
# separate models.py)
class ProductDB(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    description = Column(Text, nullable=True)
    inventory = Column(Integer, default=0)
    price = Column(Numeric(10, 2), nullable=False, default=0.00)

    orders = relationship("OrderDB", back_populates="product")


class OrderDB(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    customer_identifier = Column(String)

    product = relationship("ProductDB", back_populates="orders")


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("INFO:     MCP_DBStore: Database tables checked/created.")
