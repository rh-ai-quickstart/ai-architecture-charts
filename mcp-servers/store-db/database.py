import asyncio
import logging
import os
from enum import Enum
from typing import Optional

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.exc import OperationalError, DatabaseError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection states
class DatabaseState(Enum):
    UNKNOWN = "unknown"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    MIGRATION_FAILED = "migration_failed"
    SCHEMA_INCOMPATIBLE = "schema_incompatible"

# Database connection configuration
DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
DATABASE_USER = os.getenv("DATABASE_USER", "postgres")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "password")
DATABASE_NAME = os.getenv("DATABASE_NAME", "store_db")
DATABASE_SSL_MODE = os.getenv("DATABASE_SSL_MODE", "prefer")

# Build DATABASE_URL from components
def build_database_url():
    """Build database URL from individual components."""
    return f"postgresql+asyncpg://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}?sslmode={DATABASE_SSL_MODE}"

DATABASE_URL = build_database_url()

# Connection pool configuration
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))

# Health check configuration
HEALTH_CHECK_INTERVAL = int(os.getenv("DB_HEALTH_CHECK_INTERVAL", "30"))
HEALTH_CHECK_TIMEOUT = int(os.getenv("DB_HEALTH_CHECK_TIMEOUT", "5"))
MAX_RETRY_ATTEMPTS = int(os.getenv("DB_MAX_RETRY_ATTEMPTS", "5"))

class DatabaseManager:
    """Manages database connections with lazy initialization and health monitoring."""
    
    def __init__(self):
        self.state = DatabaseState.UNKNOWN
        self.engine = None
        self.AsyncSessionLocal = None
        self._health_check_task = None
        self._connection_attempts = 0
        self._last_health_check = 0
        self._health_check_lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize database connection and start health monitoring."""
        logger.info("Initializing database manager...")
        await self._create_engine()
        await self._check_connection()
        self._start_health_monitoring()
        
    async def _create_engine(self):
        """Create SQLAlchemy engine with connection pooling."""
        try:
            self.engine = create_async_engine(
                DATABASE_URL,
                echo=False,  # Set to True for debugging SQL
                pool_size=POOL_SIZE,
                max_overflow=MAX_OVERFLOW,
                pool_timeout=POOL_TIMEOUT,
                pool_recycle=POOL_RECYCLE,
                pool_pre_ping=True,  # Validate connections before use
            )
            
            self.AsyncSessionLocal = sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
            
            logger.info("Database engine created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            self.state = DatabaseState.DISCONNECTED
            raise
    
    async def _check_connection(self):
        """Check if database is accessible and handle initial setup."""
        async with self._health_check_lock:
            try:
                self.state = DatabaseState.CONNECTING
                logger.info("Checking database connectivity...")
                
                # Test basic connection
                async with self.engine.begin() as conn:
                    await conn.execute("SELECT 1")
                
                # Check if tables exist and handle migrations
                await self._handle_schema_setup()
                
                self.state = DatabaseState.CONNECTED
                self._connection_attempts = 0
                logger.info("Database connection established successfully")
                
            except OperationalError as e:
                if "does not exist" in str(e).lower():
                    logger.info("Database does not exist, will create on first connection")
                    self.state = DatabaseState.DISCONNECTED
                else:
                    logger.error(f"Database connection failed: {e}")
                    self.state = DatabaseState.DISCONNECTED
            except Exception as e:
                logger.error(f"Unexpected error during connection check: {e}")
                self.state = DatabaseState.DISCONNECTED
    
    async def _handle_schema_setup(self):
        """Handle database schema setup and migrations."""
        try:
            # Check if tables exist
            async with self.engine.begin() as conn:
                result = await conn.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'products'
                    );
                """)
                tables_exist = result.scalar()
            
            if not tables_exist:
                logger.info("Database tables do not exist, creating them...")
                await self._create_tables()
            else:
                logger.info("Database tables exist, checking schema compatibility...")
                await self._check_schema_compatibility()
                
        except Exception as e:
            logger.error(f"Schema setup failed: {e}")
            self.state = DatabaseState.MIGRATION_FAILED
            raise
    
    async def _create_tables(self):
        """Create database tables from SQLAlchemy models."""
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            self.state = DatabaseState.MIGRATION_FAILED
            raise
    
    async def _check_schema_compatibility(self):
        """Check if existing schema is compatible with current models."""
        try:
            # This is a basic check - in production you'd want more sophisticated schema validation
            async with self.engine.begin() as conn:
                # Check if required columns exist
                result = await conn.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'products' 
                    AND table_schema = 'public';
                """)
                columns = {row[0] for row in result.fetchall()}
                
                required_columns = {'id', 'name', 'description', 'inventory', 'price'}
                missing_columns = required_columns - columns
                
                if missing_columns:
                    logger.warning(f"Missing required columns: {missing_columns}")
                    # For now, we'll try to create tables (this will fail if they exist)
                    # In production, you'd want proper Alembic migrations here
                    await self._create_tables()
                else:
                    logger.info("Database schema is compatible")
                    
        except Exception as e:
            logger.error(f"Schema compatibility check failed: {e}")
            self.state = DatabaseState.SCHEMA_INCOMPATIBLE
            raise
    
    def _start_health_monitoring(self):
        """Start periodic health check monitoring."""
        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._health_monitor_loop())
            logger.info("Database health monitoring started")
    
    async def _health_monitor_loop(self):
        """Main health monitoring loop with exponential backoff."""
        while True:
            try:
                await asyncio.sleep(HEALTH_CHECK_INTERVAL)
                await self._perform_health_check()
                
            except asyncio.CancelledError:
                logger.info("Health monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
    
    async def _perform_health_check(self):
        """Perform a single health check."""
        if self.state == DatabaseState.CONNECTED:
            try:
                async with self.engine.begin() as conn:
                    await conn.execute("SELECT 1")
                # Connection is still good
                return
                
            except Exception as e:
                logger.warning(f"Database health check failed: {e}")
                self.state = DatabaseState.DISCONNECTED
        
        # Try to reconnect if disconnected
        if self.state == DatabaseState.DISCONNECTED:
            await self._attempt_reconnection()
    
    async def _attempt_reconnection(self):
        """Attempt to reconnect to the database with exponential backoff."""
        if self._connection_attempts >= MAX_RETRY_ATTEMPTS:
            logger.error(f"Max reconnection attempts ({MAX_RETRY_ATTEMPTS}) reached")
            return
        
        self._connection_attempts += 1
        backoff_delay = min(2 ** self._connection_attempts, 60)  # Max 60 seconds
        
        logger.info(f"Attempting database reconnection (attempt {self._connection_attempts}/{MAX_RETRY_ATTEMPTS}) in {backoff_delay}s")
        
        try:
            await asyncio.sleep(backoff_delay)
            await self._check_connection()
            
        except Exception as e:
            logger.error(f"Reconnection attempt {self._connection_attempts} failed: {e}")
    
    async def get_session(self) -> Optional[AsyncSession]:
        """Get a database session if available."""
        if self.state == DatabaseState.CONNECTED and self.AsyncSessionLocal:
            return self.AsyncSessionLocal()
        return None
    
    def get_state(self) -> DatabaseState:
        """Get current database state."""
        return self.state
    
    def is_available(self) -> bool:
        """Check if database is available for operations."""
        return self.state == DatabaseState.CONNECTED
    
    async def shutdown(self):
        """Shutdown database manager and cleanup."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        if self.engine:
            await self.engine.dispose()
        
        logger.info("Database manager shutdown complete")

# Global database manager instance
db_manager = DatabaseManager()

# SQLAlchemy Base
Base = declarative_base()

# SQLAlchemy models
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


# Legacy function for backward compatibility
async def create_db_and_tables():
    """Legacy function - now handled by DatabaseManager."""
    logger.warning("create_db_and_tables() is deprecated, use db_manager.initialize() instead")
    await db_manager.initialize()


# Legacy session maker for backward compatibility
AsyncSessionLocal = None  # Will be set by DatabaseManager

# Dependency to get DB session (now with availability check)
async def get_db() -> Optional[AsyncSession]:
    """Get database session if available."""
    if db_manager.is_available():
        session = await db_manager.get_session()
        if session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    else:
        yield None
