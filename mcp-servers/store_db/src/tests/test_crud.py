import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# Adjust these imports based on your project structure
from .. import crud, database
from ..models import ProductCreate, ProductOrderRequest


@pytest_asyncio.fixture(scope="function")  # function scope for clean DB per test
async def db_session() -> AsyncSession:
    # Ensure tables are created for each test function run in an in-memory DB or
    # test DB
    # For a persistent test DB, you might do this once per session/module.
    async with database.engine.begin() as conn:
        await conn.run_sync(
            database.Base.metadata.drop_all
        )  # Drop all first for clean state
        await conn.run_sync(database.Base.metadata.create_all)

    session = database.AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()
        # Optionally, drop tables again after tests if not using an in-memory DB
        # that vanishes
        # async with database.engine.begin() as conn:
        #     await conn.run_sync(database.Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_add_product_and_get_by_id(db_session: AsyncSession):
    """Test adding a product and retrieving it by ID."""
    product_in = ProductCreate(
        name="Test Book", description="A book for testing", inventory=10, price=19.99
    )
    created_product_db = await crud.add_product(db_session, product=product_in)
    await db_session.commit()  # Commit to save

    assert created_product_db.id is not None
    assert created_product_db.name == product_in.name
    assert created_product_db.inventory == product_in.inventory
    assert (
        float(created_product_db.price) == product_in.price
    )  # Compare as float if Numeric

    retrieved_product_db = await crud.get_product_by_id(
        db_session, product_id=created_product_db.id
    )
    assert retrieved_product_db is not None
    assert retrieved_product_db.id == created_product_db.id
    assert retrieved_product_db.name == product_in.name


@pytest.mark.asyncio
async def test_get_product_not_found(db_session: AsyncSession):
    """Test retrieving a non-existent product."""
    retrieved_product_db = await crud.get_product_by_id(db_session, product_id=99999)
    assert retrieved_product_db is None


@pytest.mark.asyncio
async def test_order_product_successful(db_session: AsyncSession):
    """Test successfully ordering a product with sufficient inventory."""
    product_in = ProductCreate(
        name="Orderable Item", description="In stock", inventory=5, price=10.00
    )
    product_db = await crud.add_product(db_session, product=product_in)
    await db_session.commit()

    order_details = ProductOrderRequest(
        product_id=product_db.id, quantity=2, customer_identifier="cust123"
    )
    created_order_db = await crud.order_product(db_session, order_details=order_details)
    await db_session.commit()

    assert created_order_db.id is not None
    assert created_order_db.product_id == product_db.id
    assert created_order_db.quantity == 2

    # Verify inventory was updated
    updated_product_db = await crud.get_product_by_id(
        db_session, product_id=product_db.id
    )
    assert updated_product_db.inventory == 3  # 5 - 2


@pytest.mark.asyncio
async def test_order_product_insufficient_inventory(db_session: AsyncSession):
    """Test ordering a product with insufficient inventory."""
    product_in = ProductCreate(
        name="Limited Stock Item", description="Low stock", inventory=1, price=25.00
    )
    product_db = await crud.add_product(db_session, product=product_in)
    await db_session.commit()

    order_details = ProductOrderRequest(
        product_id=product_db.id, quantity=2, customer_identifier="cust456"
    )

    with pytest.raises(
        ValueError, match=f"Insufficient inventory for product {product_db.name}"
    ):
        await crud.order_product(db_session, order_details=order_details)

    # Ensure no commit happened for the order part by rolling back or checking state
    # The crud function itself raises before commit in this case, so
    # session.commit() wouldn't be reached in the tool.
    # Here, we check product inventory remained unchanged.
    await db_session.rollback()  # Rollback any potential changes from the
    # failed order attempt

    check_product_db = await crud.get_product_by_id(
        db_session, product_id=product_db.id
    )
    assert check_product_db.inventory == 1  # Inventory should not have changed


@pytest.mark.asyncio
async def test_order_product_not_found(db_session: AsyncSession):
    """Test ordering a product that does not exist."""
    order_details = ProductOrderRequest(
        product_id=999, quantity=1, customer_identifier="cust789"
    )
    with pytest.raises(ValueError, match="Product with id 999 not found"):
        await crud.order_product(db_session, order_details=order_details)


@pytest.mark.asyncio
async def test_search_products(db_session: AsyncSession):
    """Test searching for products."""
    await crud.add_product(
        db_session, ProductCreate(name="Alpha Game", inventory=10, price=59.99)
    )
    await crud.add_product(
        db_session, ProductCreate(name="Beta Game Console", inventory=5, price=299.99)
    )
    await crud.add_product(
        db_session, ProductCreate(name="Alpha Accessories", inventory=20, price=19.99)
    )
    await db_session.commit()

    results_alpha = await crud.search_products(db_session, query="Alpha")
    assert len(results_alpha) == 2
    assert any(p.name == "Alpha Game" for p in results_alpha)
    assert any(p.name == "Alpha Accessories" for p in results_alpha)

    results_game = await crud.search_products(db_session, query="Game")
    assert len(results_game) == 2
    assert any(p.name == "Alpha Game" for p in results_game)
    assert any(p.name == "Beta Game Console" for p in results_game)

    results_nothing = await crud.search_products(db_session, query="XYZNoSuchProduct")
    assert len(results_nothing) == 0
