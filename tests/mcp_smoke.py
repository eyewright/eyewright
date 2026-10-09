"""Stdio smoke test for `eyewright mcp` (run with the mcp extra):

    uv run --extra mcp python tests/mcp_smoke.py
"""

import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(command="uv", args=["run", "eyewright", "mcp"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("tools:", [t.name for t in tools.tools])
            res = await session.call_tool(
                "eyewright_gate",
                {"state": "The sky is blue.", "question": "Is the statement true?"},
            )
            print("gate result:", res.content[0].text[:300])


if __name__ == "__main__":
    asyncio.run(main())