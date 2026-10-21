"""Stdio smoke test for `eyewright mcp` — the same bare launch path harnesses use:

    uv run python tests/mcp_smoke.py

Needs the `mcp` package (default `runtime` group, or the `mcp` extra). The live
gate call needs the local services (laya-serve :8000, Ollama :11434).
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
            names = {t.name for t in tools.tools}
            print("tools:", sorted(names))
            assert names == {"eyewright_gate", "eyewright_ask"}, names
            res = await session.call_tool(
                "eyewright_gate",
                {"state": "The sky is blue.", "question": "Is the statement true?"},
            )
            print("gate result:", res.content[0].text[:300])


if __name__ == "__main__":
    asyncio.run(main())