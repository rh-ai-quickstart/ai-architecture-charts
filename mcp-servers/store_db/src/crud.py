from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

"""
Ensure these imports point to the models and database modules within the
mcp_dbstore directory.
"""
from . import database, models  # Changed from appservers.store to relative imports


async def get_product_by_id(
    db: AsyncSession, product_id: int
) -> database.ProductDB | None:  # Return DB model
    result = await db.execute(
        select(database.ProductDB).filter(database.ProductDB.id == product_id)
    )
    return result.scalars().first()


async def get_product_by_name(
    db: AsyncSession, name: str
) -> database.ProductDB | None:  # Return DB model
    result = await db.execute(
        select(database.ProductDB).filter(database.ProductDB.name == name)
    )
    return result.scalars().first()


async def get_products(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[database.ProductDB]:  # Return list of DB models
    result = await db.execute(select(database.ProductDB).offset(skip).limit(limit))
    return result.scalars().all()


async def search_products(
    db: AsyncSession, query: str, skip: int = 0, limit: int = 100
) -> list[database.ProductDB]:  # Return list of DB models
    search_term = f"%{query}%"
    result = await db.execute(
        select(database.ProductDB)
        .filter(
            or_(
                database.ProductDB.name.ilike(search_term),
                database.ProductDB.description.ilike(search_term),
            )
        )
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def add_product(
    db: AsyncSession, product: models.ProductCreate
) -> database.ProductDB:  # Return DB model
    db_product = database.ProductDB(**product.model_dump())
    db.add(db_product)
    await db.flush()
    await db.refresh(db_product)
    return db_product


async def remove_product(
    db: AsyncSession, product_id: int
) -> database.ProductDB | None:  # Return DB model
    # Fetch the product to be deleted within the current session
    result = await db.execute(
        select(database.ProductDB).filter(database.ProductDB.id == product_id)
    )
    db_product = result.scalars().first()
    if db_product:
        await db.delete(db_product)
        await db.flush()
        return db_product
    return None


async def order_product(
    db: AsyncSession, order_details: models.ProductOrderRequest
) -> database.OrderDB:  # Return DB model
    # Get product within the current session
    product_result = await db.execute(
        select(database.ProductDB).filter(
            database.ProductDB.id == order_details.product_id
        )
    )
    db_product = product_result.scalars().first()

    if not db_product:
        raise ValueError(f"Product with id {order_details.product_id} not found.")

    if db_product.inventory < order_details.quantity:
        raise ValueError(
            f"Not enough inventory for product '{db_product.name}'. "
            f"Available: {db_product.inventory}, "
            f"Requested: {order_details.quantity}"
        )

    db_product.inventory -= order_details.quantity

    db_order = database.OrderDB(
        product_id=order_details.product_id,
        quantity=order_details.quantity,
        customer_identifier=order_details.customer_identifier,
    )
    db.add(db_product)  # Add updated product (inventory change) to session
    db.add(db_order)

    await db.flush()
    await db.refresh(db_order)
    await db.refresh(db_product)
    return db_order
