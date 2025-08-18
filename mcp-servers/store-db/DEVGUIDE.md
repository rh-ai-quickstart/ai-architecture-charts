# MCP DBStore Development Guide

This guide covers development setup, testing, and contribution guidelines for the MCP DBStore server.

## Development Setup

### Prerequisites
- Python 3.12+
- PostgreSQL 15+
- Git
- Docker (optional)

### Local Environment Setup

1. **Clone and Navigate**
   ```bash
   git clone <repository>
   cd mcpservers/mcp-store-db
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # If exists
   ```

4. **Database Setup**
   ```bash
   # Option 1: Using podman compose (recommended)
# Use the main compose.yaml file in the parent directory
podman compose -f ../compose.yaml up -d postgresql

   # Option 2: Manual setup (if not using compose)
   # First start PostgreSQL, then create database:
   psql -h localhost -U postgres -c "CREATE DATABASE store_db;"

   # Verify database connection
   psql "postgresql://postgres:password@localhost:5432/store_db" -c "SELECT 1;"
   ```

5. **Environment Configuration**
   ```bash
   # Create .env file
   cat > .env << EOF
   DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/store_db
   LOG_LEVEL=DEBUG
   EOF
   ```

## Project Structure

```
mcp-store-db/
├── store.py              # Main MCP server
├── models.py             # Pydantic data models
├── database.py           # SQLAlchemy database models
├── crud.py               # Database operations
├── requirements.txt      # Python dependencies
├── Containerfile         # Container build instructions
├── populate_db.sql       # Sample data
├── helm/                 # Kubernetes deployment
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
├── tests/                # Test suite
│   ├── test_crud.py
│   └── test_mcp_tools.py
└── debug/
    └── deploy.yaml       # Debug deployment
```

## Development Workflow

### Running the Server

```bash
# Development mode with auto-reload
python store.py

# With custom database URL
DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db" python store.py

# Check server health
curl http://localhost:8002/health  # If health endpoint exists
```

### Adding to LlamaStack

```bash
# Option 1: Using LlamaStack CLI (if available)
llamastack mcp-server add \
  --name mcp-dbstore \
  --url http://localhost:8002 \
  --description "Database store MCP server"

# Option 2: Manual configuration in config.yaml
cat >> llamastack-config.yaml << EOF
mcp_servers:
  - name: mcp-dbstore
    url: http://localhost:8002
    description: "Direct database access for inventory management"
    tools:
      - get_products
      - add_product
      - order_product
EOF
```

### Database Operations

```bash
# Reset database
python -c "
import asyncio
from database import create_db_and_tables
asyncio.run(create_db_and_tables())
"

# Populate sample data
psql $DATABASE_URL -f populate_db.sql
```

### Testing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_crud.py -v

# Run with coverage
pytest --cov=. tests/

# Test specific functionality
pytest tests/test_mcp_tools.py::test_tool_add_product_and_get_products -v
```

### Code Quality

```bash
# Format code
black .
isort .

# Lint code
flake8 .
mypy .

# Pre-commit hooks
pre-commit run --all-files
```

## Architecture Details

### Database Layer

```mermaid
erDiagram
    ProductDB {
        int id PK
        string name UK
        text description
        int inventory
        numeric price
    }

    OrderDB {
        int id PK
        int product_id FK
        int quantity
        string customer_identifier
    }

    ProductDB ||--o{ OrderDB : "has orders"
```

### MCP Integration

```mermaid
sequenceDiagram
    participant Agent
    participant MCP as MCP Server
    participant DB as Database

    Agent->>MCP: get_products()
    MCP->>DB: SELECT * FROM products
    DB-->>MCP: Product list
    MCP-->>Agent: JSON response

    Agent->>MCP: order_product(id, qty)
    MCP->>DB: BEGIN TRANSACTION
    MCP->>DB: SELECT inventory WHERE id=?
    MCP->>DB: UPDATE inventory SET inventory=inventory-qty
    MCP->>DB: INSERT INTO orders
    MCP->>DB: COMMIT
    DB-->>MCP: Order confirmation
    MCP-->>Agent: Order details
```

## Adding New Features

### Adding a New Tool

1. **Define the Tool Function**
   ```python
   @mcp_server.tool()
   async def my_new_tool(param1: str, param2: int) -> Dict[str, Any]:
       """Tool description for LLM reasoning.

       Args:
           param1: Description of parameter 1
           param2: Description of parameter 2

       Returns:
           Dictionary with result data
       """
       async with AsyncSessionLocal() as session:
           # Your implementation here
           result = await crud.my_crud_operation(session, param1, param2)
           return result.model_dump()
   ```

2. **Add CRUD Operation**
   ```python
   # In crud.py
   async def my_crud_operation(
       db: AsyncSession, param1: str, param2: int
   ) -> database.MyModel:
       # Database operation implementation
       pass
   ```

3. **Add Tests**
   ```python
   # In tests/test_mcp_tools.py
   @pytest.mark.asyncio
   async def test_my_new_tool(initialized_test_mcp_server):
       # Test implementation
       pass
   ```

### Database Schema Changes

1. **Update Models**
   ```python
   # In database.py
   class NewTableDB(Base):
       __tablename__ = "new_table"
       id = Column(Integer, primary_key=True)
       # Add columns
   ```

2. **Create Migration** (if using Alembic)
   ```bash
   alembic revision --autogenerate -m "Add new table"
   alembic upgrade head
   ```

## Testing Strategy

### Unit Tests
- Test individual CRUD operations
- Test data model validation
- Test error handling

### Integration Tests
- Test MCP tool functions end-to-end
- Test database transactions
- Test concurrent operations

### Test Database Setup
```python
# Use in-memory SQLite for fast tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession)
    async with async_session() as session:
        yield session
```

## Container Development

### Building Images
```bash
# Build development image
docker build -t mcp-dbstore:dev .

# Build with specific tag
docker build -t quay.io/ecosystem-appeng/mcp-dbstore:latest .

# Multi-platform build
docker buildx build --platform linux/amd64,linux/arm64 \
  -t quay.io/ecosystem-appeng/mcp-dbstore:latest .
```

### Local Container Testing
```bash
# Run with development database
docker run --rm -p 8002:8002 \
  -e DATABASE_URL="postgresql+asyncpg://postgres:password@host.docker.internal:5432/store_db" \
  mcp-dbstore:dev

# Run with docker-compose
cat > docker-compose.dev.yml << EOF
services:
  mcp-dbstore:
    build: .
    ports: ["8002:8002"]
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:password@db:5432/store_db
    depends_on: [db]

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_PASSWORD: password
      POSTGRES_DB: store_db
    ports: ["5432:5432"]
EOF

docker-compose -f docker-compose.dev.yml up
```

## Helm Chart Development

### Local Chart Testing
```bash
# Lint chart
helm lint ./helm

# Template rendering
helm template test-release ./helm

# Install locally
helm install mcp-dbstore-dev ./helm \
  --set image.tag=dev \
  --set postgresql.auth.postgresPassword=devpassword

# Upgrade
helm upgrade mcp-dbstore-dev ./helm
```

### Chart Customization
```yaml
# values-dev.yaml
image:
  tag: dev
  pullPolicy: Never

postgresql:
  auth:
    postgresPassword: devpassword
  primary:
    persistence:
      enabled: false  # For development
```

## Debugging

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Check database connectivity
   psql $DATABASE_URL -c "SELECT 1;"

   # Verify connection pool settings
   python -c "
   from database import engine
   print(f'Pool size: {engine.pool.size()}')
   print(f'Pool checked out: {engine.pool.checkedout()}')
   "
   ```

2. **MCP Tool Registration**
   ```python
   # List registered tools
   python -c "
   import store
   print('Registered tools:')
   for tool_name in dir(store.mcp_server):
       if not tool_name.startswith('_'):
           print(f'  - {tool_name}')
   "
   ```

3. **Performance Issues**
   ```bash
   # Enable SQL logging
   export LOG_LEVEL=DEBUG
   python store.py  # Will show SQL queries
   ```

### Debug Mode
```python
# In store.py, add:
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable SQL echo
engine = create_async_engine(DATABASE_URL, echo=True)
```

## Contributing

### Code Style
- Use Black for formatting
- Follow PEP 8 guidelines
- Add type hints to all functions
- Include docstrings for all public functions

### Pull Request Process
1. Create feature branch from `main`
2. Add tests for new functionality
3. Update documentation if needed
4. Ensure all tests pass
5. Submit pull request with clear description

### Commit Messages
```
feat: add product search by category tool
fix: handle database connection timeout
docs: update development setup guide
test: add integration tests for order processing
```

## Performance Optimization

### Database Optimization
- Use appropriate indexes
- Implement connection pooling
- Consider read replicas for heavy read workloads
- Monitor query performance

### MCP Server Optimization
- Use async/await properly
- Implement caching where appropriate
- Monitor memory usage
- Profile bottlenecks

This development guide provides comprehensive coverage for contributing to and maintaining the MCP DBStore server.
