# MCP Store-DB

An integrated Model Context Protocol (MCP) server with **lazy database connection management** and direct PostgreSQL connectivity for inventory management. This server provides AI agents with access to a store database while gracefully handling database unavailability so that it can be deployed with its own database or wihout one by way of using an external database while gracefully handling loss of database connectivity.

## Overview

MCP DBStore combines an MCP server with intelligent database connectivity that won't crash if the database is unavailable. It automatically creates tables, runs migrations, and provides meaningful error messages when database operations cannot be performed.

## Key Features

### 🚀 **Lazy Database Connection Management**
- **Graceful Degradation**: Server starts and runs even when database is unavailable
- **Automatic Reconnection**: Exponential backoff retry mechanism with configurable limits
- **Health Monitoring**: Continuous database connectivity monitoring with status reporting
- **Smart Error Handling**: Meaningful error messages for LLM agents when database is down

### 🔧 **Database Operations**
- **Auto-Initialization**: Creates tables automatically on first successful connection
- **Migration Support**: Alembic-based schema migration system
- **Connection Pooling**: Efficient database connection management
- **Schema Validation**: Checks compatibility and reports issues gracefully

### 📊 **Health & Monitoring**
- **Separate Health States**: MCP server health independent of database status
- **Detailed Status Reporting**: Clear indication of database connectivity state
- **Kubernetes Friendly**: Won't be restarted when only database is unavailable

## Architecture

```mermaid
graph LR
    subgraph "AI Agent Platform"
        Agent[AI Agent]
        LlamaStack[LlamaStack]
    end

    subgraph "MCP DBStore"
        MCP[MCP Server<br/>Port 8002]
        Health[Health Monitor]
        DBManager[Database Manager]
    end

    subgraph "Database Layer"
        PG[(PostgreSQL<br/>Optional)]
    end

    Agent --> LlamaStack
    LlamaStack --> MCP
    MCP --> Health
    MCP --> DBManager
    DBManager -.->|Lazy Connection| PG

    style MCP fill:#e1f5fe
    style DBManager fill:#fff3e0
    style PG fill:#f3e5f5
```

**Port Information:**
- **Container Port**: 8002 (internal service port)
- **Local Development**: 8002 (when using compose.yaml)
- **Kubernetes**: 8002 (standard deployment)

## Database Connection States

The server reports one of these database states:

| State | Description | MCP Tools Behavior |
|-------|-------------|-------------------|
| `connected` | Database available and ready | All tools work normally |
| `disconnected` | Database unavailable | Tools return clear error messages |
| `connecting` | Attempting to connect | Tools return "connecting" status |
| `migration_failed` | Schema setup failed | Tools report migration issues |
| `schema_incompatible` | Schema version mismatch | Tools report compatibility issues |

## Database Requirements

**Important**: The MCP server requires a PostgreSQL database to be available. You have two options:

### Option 1: Use External PostgreSQL (Recommended)
- **pgvector Instance**: By default, the server connects to the `pgvector` PostgreSQL instance
- **Database Creation**: You must create the `store_db` database in your PostgreSQL instance before deployment
- **Connection**: The server will automatically create tables and populate initial data on first connection

### Option 2: Deploy PostgreSQL with Helm
- Set `postgresql.enabled: true` in your values.yaml
- The server will deploy its own PostgreSQL instance

### Database Setup Commands
```sql
-- Connect to your PostgreSQL instance
psql -h <host> -U <user> -d <database>

-- Create the store_db database
CREATE DATABASE store_db;

-- Verify the database was created
\l
```

## Quick Start

### Local Development
```bash
# Navigate to directory
cd mcpservers/mcp-store-db

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Option 1: Start with existing database
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/store_db"
python store.py

# Option 2: Use compose for full local setup
podman compose up -d
```

### Using Make Commands
```bash
# Quick development setup
make dev

# Check server status
make status

# View logs
make logs

# Stop server
make stop
```

### Podman Deployment
```bash
# Build container
podman build -t mcp-store-db .

# Run with database connection
podman run -p 8002:8002 \
  -e DATABASE_URL="postgresql+asyncpg://user:password@db:5432/store_db" \
  mcp-dbstore
```

### Kubernetes Deployment
```bash
# Deploy without PostgreSQL (connect to existing database)
helm install mcp-store-db ./helm \
  --set postgresql.enabled=false \
  --set env.DATABASE_URL="postgresql+asyncpg://user:pass@existing-db:5432/store_db"

# Deploy with PostgreSQL included
helm install mcp-store-db ./helm \
  --set postgresql.enabled=true \
  --set postgresql.auth.postgresPassword=yourpassword
```

## Available Tools

| Tool | Description | Database Required |
|------|-------------|------------------|
| `get_products` | List all products with pagination | ✅ Yes |
| `get_product_by_id` | Get specific product by ID | ✅ Yes |
| `get_product_by_name` | Get product by exact name | ✅ Yes |
| `search_products` | Search products by query | ✅ Yes |
| `add_product` | Create new product | ✅ Yes |
| `remove_product` | Delete product by ID | ✅ Yes |
| `order_product` | Place order (reduces inventory) | ✅ Yes |
| `health_check` | Check server and database status | ❌ No |
| `check_database_connectivity` | Check database availability | ❌ No |

## Configuration

### Environment Variables
```bash
# Required: Database connection
DATABASE_URL="postgresql+asyncpg://user:password@host:port/database"

# Optional: Connection pool settings
DB_POOL_SIZE=10                    # Connection pool size
DB_MAX_OVERFLOW=20                 # Maximum overflow connections
DB_POOL_TIMEOUT=30                 # Connection timeout (seconds)
DB_POOL_RECYCLE=3600               # Connection recycle time (seconds)

# Optional: Health check settings
DB_HEALTH_CHECK_INTERVAL=30        # Health check interval (seconds)
DB_HEALTH_CHECK_TIMEOUT=5          # Health check timeout (seconds)
DB_MAX_RETRY_ATTEMPTS=5            # Maximum reconnection attempts
```

### Health Check Response
```json
{
  "status": "healthy",              // MCP server is always healthy if running
  "service": "mcp-store-db",
  "database_status": "connected",   // Database connectivity state
  "database_available": true,       // Whether database operations are possible
  "database_url": "postgresql+...",
  "message": "MCP server is running and ready to process requests"
}
```

## Database Migration

### Using Alembic
```bash
# Initialize migrations (first time only)
make db-init

# Create new migration
make db-migrate

# Apply migrations
make db-upgrade

# Rollback migration
make db-downgrade

# Reset database
make db-reset
```

### Migration States
- **No Tables**: Automatically creates tables from SQLAlchemy models
- **Existing Tables**: Checks schema compatibility and reports issues
- **Schema Mismatch**: Reports incompatibility without crashing

## Use Cases

### ✅ **Best For**
- Production environments requiring high availability
- Scenarios where database may be temporarily unavailable
- Kubernetes deployments with independent database scaling
- Development environments with intermittent database access
- Systems requiring graceful degradation

### ⚠️ **Consider Alternatives When**
- Simple, always-on database connectivity is sufficient
- Minimal complexity is preferred over resilience
- Database and application must always be deployed together

## Performance

- **Throughput**: ~1000 requests/second (when database is available)
- **Latency**: <10ms for simple queries (when database is available)
- **Memory Usage**: ~50MB base + connection pool
- **Startup Time**: <2 seconds (regardless of database status)
- **Reconnection**: Exponential backoff with configurable limits

## Monitoring

### Health Check Endpoints
- **`/health`**: Overall server and database status
- **`/tools`**: List of available MCP tools

### Database Status Monitoring
```bash
# Check server health
curl http://localhost:8002/health | jq '.database_status'

# Monitor database connectivity
curl http://localhost:8002/health | jq '.database_available'
```

## Error Handling

### When Database is Unavailable
```python
# MCP tools return clear error messages
try:
    products = await get_products()
except RuntimeError as e:
    if "Database is currently unavailable" in str(e):
        print("Database is down, check connectivity")
    else:
        print(f"Other error: {e}")
```

### Database Connectivity Check Tool
```python
# LLM agents can check database status before operations
status = await check_database_connectivity()
if not status["can_perform_operations"]:
    print(f"Database unavailable: {status['status_message']}")
```

## Support

For technical support and development:
- Review the [Development Guide](DEVGUIDE.md)
- Check the [User Guide](USERGUIDE.md) for usage examples
- Use `make help` for available commands
- See the main [MCP Servers documentation](../README.md)
