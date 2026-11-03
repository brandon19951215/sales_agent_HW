"""Sales data exposed through MCP Streamable HTTP."""

import os

from mcp.server import MCPServer


mcp = MCPServer("SalesTools")

sales_data = {
    "Singapore": {
        "2026-Q1": 100,
        "2026-Q2": 200,
        "2026-Q3": 300,
    }
}


@mcp.tool()
def get_sales(region: str, period: str):
    """Get actual sales for a region and period."""
    if region not in sales_data:
        return {"error": f"Region '{region}' not found."}

    if period not in sales_data[region]:
        return {"error": f"Period '{period}' not found."}

    return sales_data[region][period]


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=os.getenv("MCP_HOST", "127.0.0.1"),
        port=int(os.getenv("MCP_PORT", "8001")),
        stateless_http=True,
        json_response=True,
    )
