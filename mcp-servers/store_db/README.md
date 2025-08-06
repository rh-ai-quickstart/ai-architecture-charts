# MCP DBStore

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP Protocol](https://img.shields.io/badge/MCP-Protocol-green.svg)](https://modelcontextprotocol.io/)

A **Model Context Protocol (MCP) server** that provides AI agents with intelligent access to inventory management systems. Built with FastMCP and PostgreSQL, MCP DBStore enables LLMs to answer questions about product availability, pricing, and inventory levels through natural language interactions.

## 🎯 What is MCP DBStore?

MCP DBStore transforms your product inventory into an AI-accessible knowledge base. Instead of requiring users to learn complex database queries or inventory management systems, they can simply ask questions like:

- *"What products do we have in stock?"*
- *"How much does the Super Widget cost?"*
- *"Do we have any quantum related products available?"*
- *"Place an order for 5 Mega Gadgets for customer John Smith"*

The server provides 7 specialized tools that handle everything from browsing the product catalog to processing orders and updating inventory levels.

## 🚀 Quick Start

### Prerequisites
- Kubernetes cluster with Helm 3.2+
- `kubectl` configured

### Deploy in Minutes
```bash
# Clone the repository
git clone https://github.com/rh-ai-kickstart/ai-architecture-charts.git
cd ai-architecture-charts/mcp-servers

# Deploy with Helm
helm install mcp-dbstore ./store_db/helm/mcp-dbstore

# Wait for deployment (2-3 minutes)
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=mcp-dbstore --timeout=300s
```

### Test Your Deployment
```bash
# Port forward to access the server
kubectl port-forward svc/mcp-dbstore-mcp-server 8002:8002 &

# Install MCP inspector for testing
pip install mcp-inspector

# Test the server
mcp-inspector http://localhost:8002
```

## 🛠️ Available Tools

MCP DBStore provides 7 specialized tools for inventory management:

| Tool | Purpose | Example Use |
|------|---------|-------------|
| `get_products` | Browse entire product catalog | "Show me all available products" |
| `get_product_by_id` | Get specific product details | "What's the price of product ID 123?" |
| `search_products` | Find products by name/description | "Find all quantum-related products" |
| `add_product` | Create new inventory items | "Add a new product called 'Smart Speaker'" |
| `remove_product` | Delete products from catalog | "Remove the discontinued product" |
| `order_product` | Process orders & update inventory | "Order 5 widgets for customer Alice" |
| `get_product_by_name` | Exact product name lookup | "Get details for 'Super Widget'" |

## 🔗 Integration Examples

### With LlamaStack
```bash
# Register the MCP server
curl -X POST localhost:8321/v1/toolgroups \
  -H "Content-Type: application/json" \
  --data '{
    "provider_id": "model-context-protocol",
    "toolgroup_id": "mcp::dbstore",
    "mcp_endpoint": {
      "uri": "http://mcp-dbstore-mcp-server.default.svc.cluster.local:8002/sse"
    }
  }'
```

### Direct API Usage
```python
import aiohttp

async def get_product_info():
    async with aiohttp.ClientSession() as session:
        # Get all products
        async with session.post("http://localhost:8002/tools/get_products") as resp:
            products = await resp.json()
        
        # Search for specific products
        async with session.post(
            "http://localhost:8002/tools/search_products",
            json={"query": "widget"}
        ) as resp:
            results = await resp.json()
```

## 📊 Sample Data

The deployment includes 10 sample products to get you started:
- **Super Widget** - $29.99 (100 units)
- **Mega Gadget** - $79.50 (50 units)
- **Quantum Sprocket** - $199.00 (30 units)
- And 7 more products with varying prices and inventory levels

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   LLM Agent     │    │   MCP DBStore    │    │   PostgreSQL    │
│                 │    │     Server       │    │    Database     │
│ - Natural       │◄──►│ - FastMCP        │◄──►│ - Products      │
│   Language      │    │ - SQLAlchemy     │    │ - Orders        │
│ - Tool Calls    │    │ - Async Tools    │    │ - ACID          │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

**Technology Stack:**
- **Protocol**: Model Context Protocol (MCP)
- **Framework**: FastMCP for high-performance async MCP servers
- **Database**: PostgreSQL 15 with SQLAlchemy async ORM
- **Container**: Docker with Kubernetes deployment
- **Package Manager**: Helm charts for easy deployment

## 📚 Documentation

- **[Quick Start Guide](docs/mcp-dbstore-quickstart.md)** - Detailed deployment and testing instructions
- **[Developer Guide](docs/mcp-dbstore-developer-guide.md)** - Architecture, patterns, and best practices
- **[Developer Reference](docs/mcp-dbstore-developer-reference.md)** - Concise reference for extending the server
- **[Helm Chart README](../../deploy/helm/mcp-dbstore/README.md)** - Deployment configuration options

## 🤝 Contributing

We welcome contributions! Here's how you can help:

### Development Setup
```bash
# Clone and setup development environment
git clone https://github.com/rh-ai-kickstart/ai-architecture-charts.git
cd ai-architecture-charts/mcp-servers/store_db/src

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up local PostgreSQL
docker run --name dev-postgres \
  -e POSTGRES_USER=mcpuser \
  -e POSTGRES_PASSWORD=mcppassword \
  -e POSTGRES_DB=store_db \
  -p 5432:5432 \
  -d postgres:15-alpine

# Run the server
python -m mcpservers.mcp_dbstore.store
```

### Areas for Contribution
- **New Tools**: Add domain-specific inventory management tools
- **Enhanced Analytics**: Create tools for inventory insights and reporting
- **Performance**: Optimize database queries and connection pooling
- **Security**: Implement authentication and authorization
- **Testing**: Add comprehensive test coverage
- **Documentation**: Improve guides and examples

### Getting Started
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../../LICENSE) file for details.

## 🙏 Acknowledgments

- [Model Context Protocol](https://modelcontextprotocol.io/) for the standardized agent-tool communication
- [FastMCP](https://github.com/jlowin/fastmcp) for the high-performance MCP server framework
- [LlamaStack](https://github.com/meta-llama/llama-stack) for AI agent orchestration
- The open source community for inspiration and collaboration

## 🔗 Related Projects

- [AI Virtual Assistant](https://github.com/yourusername/ai-virtual-assistant) - Main project repository
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector) - Tool for testing MCP servers
- [LlamaStack](https://github.com/meta-llama/llama-stack) - AI agent framework

---

**Made with ❤️ for the open source community**

Questions? Issues? Ideas? [Open an issue](https://github.com/rh-ai-kickstart/ai-architecture-charts/issues) or join our discussions! 