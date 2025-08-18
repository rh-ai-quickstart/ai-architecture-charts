from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import OperationalError, DatabaseError

"""
Ensure these imports point to the models and database modules within the
mcp-store-db directory.
"""
import database
import models

class DatabaseUnavailableError(Exception):
    """Raised when the database is not available."""
    pass

class DatabaseOperationError(Exception):
    """Raised when a database operation fails."""
    pass

async def _ensure_database_available():
    """Ensure database is available before performing operations."""
    if not database.db_manager.is_available():
        state = database.db_manager.get_state()
        if state == database.DatabaseState.DISCONNECTED:
            raise DatabaseUnavailableError(
                "Database is currently unavailable. Please check your database connection "
                "and ensure the PostgreSQL service is running."
            )
        elif state == database.DatabaseState.MIGRATION_FAILED:
            raise DatabaseUnavailableError(
                "Database migration failed. The database schema may be incompatible. "
                "Please check the server logs for details."
            )
        elif state == database.DatabaseState.SCHEMA_INCOMPATIBLE:
            raise DatabaseUnavailableError(
                "Database schema is incompatible with the current application version. "
                "Manual database migration may be required."
            )
        else:
            raise DatabaseUnavailableError(
                f"Database is in an unknown state: {state.value}. "
                "Please check the server logs for details."
            )

async def get_product_by_id(
    db: AsyncSession, product_id: int
) -> database.ProductDB | None:  # Return DB model
    """Retrieve a product by its ID."""
    await _ensure_database_available()
    
    try:
        result = await db.execute(
            select(database.ProductDB).filter(database.ProductDB.id == product_id)
        )
        return result.scalars().first()
    except (OperationalError, DatabaseError) as e:
        raise DatabaseOperationError(f"Database operation failed: {str(e)}")
    except Exception as e:
        raise DatabaseOperationError(f"Unexpected error: {str(e)}")


async def get_product_by_name(
    db: AsyncSession, name: str
) -> database.ProductDB | None:  # Return DB model
    """Retrieve a product by its name."""
    await _ensure_database_available()
    
    try:
        result = await db.execute(
            select(database.ProductDB).filter(database.ProductDB.name == name)
        )
        return result.scalars().first()
    except (OperationalError, DatabaseError) as e:
        raise DatabaseOperationError(f"Database operation failed: {str(e)}")
    except Exception as e:
        raise DatabaseOperationError(f"Unexpected error: {str(e)}")


async def get_products(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[database.ProductDB]:  # Return list of DB models
    """Retrieve a list of products with pagination."""
    await _ensure_database_available()
    
    try:
        result = await db.execute(select(database.ProductDB).offset(skip).limit(limit))
        return result.scalars().all()
    except (OperationalError, DatabaseError) as e:
        raise DatabaseOperationError(f"Database operation failed: {str(e)}")
    except Exception as e:
        raise DatabaseOperationError(f"Unexpected error: {str(e)}")


async def search_products(
    db: AsyncSession, query: str, skip: int = 0, limit: int = 100
) -> list[database.ProductDB]:  # Return list of DB models
    """Search products by name or description."""
    await _ensure_database_available()
    
    try:
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
    except (OperationalError, DatabaseError) as e:
        raise DatabaseOperationError(f"Database operation failed: {str(e)}")
    except Exception as e:
        raise DatabaseOperationError(f"Unexpected error: {str(e)}")


async def add_product(
    db: AsyncSession, product: models.ProductCreate
) -> database.ProductDB:  # Return DB model
    """Add a new product to the database."""
    await _ensure_database_available()
    
    try:
        db_product = database.ProductDB(**product.model_dump())
        db.add(db_product)
        await db.flush()  # Get ID before commit
        await db.refresh(db_product)
        return db_product
    except (OperationalError, DatabaseError) as e:
        raise DatabaseOperationError(f"Database operation failed: {str(e)}")
    except Exception as e:
        raise DatabaseOperationError(f"Unexpected error: {str(e)}")


async def remove_product(
    db: AsyncSession, product_id: int
) -> database.ProductDB | None:  # Return DB model
    """Remove a product from the database."""
    await _ensure_database_available()
    
    try:
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
    except (OperationalError, DatabaseError) as e:
        raise DatabaseOperationError(f"Database operation failed: {str(e)}")
    except Exception as e:
        raise DatabaseOperationError(f"Unexpected error: {str(e)}")


async def order_product(
    db: AsyncSession, order_details: models.ProductOrderRequest
) -> database.OrderDB:  # Return DB model
    """Place an order for a product, reducing inventory."""
    await _ensure_database_available()
    
    try:
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

        # Reduce inventory
        db_product.inventory -= order_details.quantity

        # Create order
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
        
    except ValueError:
        # Re-raise ValueError as-is (business logic errors)
        raise
    except (OperationalError, DatabaseError) as e:
        raise DatabaseOperationError(f"Database operation failed: {str(e)}")
    except Exception as e:
        raise DatabaseOperationError(f"Unexpected error: {str(e)}")
