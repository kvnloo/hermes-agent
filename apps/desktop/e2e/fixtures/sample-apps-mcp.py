"""Sample-app MCP servers for the ephemeral-ui card e2e (apps/desktop/e2e/ephemeral-cards.spec.ts).

    python sample-apps-mcp.py gmail|google_calendar|github

One stdio MCP server per app, so Hermes registers real `mcp__<app>__<tool>` tools and the desktop
renders real MCP tool calls. Every value is synthetic sample data; nothing reaches a real account.
"""

import sys

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as MCPServer

APP = sys.argv[1] if len(sys.argv) > 1 else "gmail"
server = MCPServer(APP)

if APP == "gmail":

    @server.tool()
    def search_threads(query: str = "in:inbox is:unread") -> dict:
        """Search mail threads (sample data)."""
        return {
            "query": query,
            "sample": True,
            "threads": [
                {"id": "t-4512", "from": "Dana (Acme)", "subject": "Q3 review: final deck attached", "unread": True},
                {"id": "t-4513", "from": "Billing (Northwind)", "subject": "Invoice #4512 due Friday", "unread": True},
                {"id": "t-4514", "from": "Sam (Acme)", "subject": "Can we move the review to 2pm?", "unread": True},
            ],
        }

elif APP == "google_calendar":

    @server.tool()
    def find_free_slots(day: str = "tuesday", minutes: int = 30) -> dict:
        """Find open calendar slots (sample data)."""
        return {"day": day, "minutes": minutes, "sample": True, "slots": ["10:00", "13:30", "16:00"]}

elif APP == "github":

    @server.tool()
    def get_check_runs(repo: str = "acme/web", ref: str = "main") -> dict:
        """List CI check runs for a ref (sample data)."""
        return {
            "repo": repo,
            "ref": ref,
            "sample": True,
            "checks": [
                {"name": "build", "status": "success"},
                {"name": "unit", "status": "success"},
                {"name": "lint", "status": "failure"},
            ],
        }

if __name__ == "__main__":
    server.run()
