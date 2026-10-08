"""oracle mcp - the Oracle as MCP tools for any AI harness.

Tools:
  oracle_gate(state, question)          -> three-eye gate: p_done + decision + trace
  oracle_ask(state, question, choices?) -> typed decision (yes/no, or pick a choice)

Run as a stdio MCP server: ``oracle mcp`` (needs the ``mcp`` extra:
``uv run --extra mcp oracle mcp``).
"""

from mcp.server.mcpserver import MCPServer

from .decide import ask
from .gate import decide_gate


def build(cfg):
    mcp = MCPServer("oracle")

    @mcp.tool()
    def oracle_gate(state: str, question: str) -> dict:
        """Gate a claim against the Oracle committee.

        Returns p_done, the policy decision (accept / consensus-* / review-*),
        and the full consult trace.
        """
        p, trace = decide_gate(cfg, state, question)
        return {"p_done": round(p, 4), "decision": trace.get("decision"), "trace": trace}

    @mcp.tool()
    def oracle_ask(state: str, question: str, choices: dict | None = None, engine: str | None = None) -> dict:
        """Ask the Oracle a typed decision.

        With `choices` (option -> description) it picks an option; without, it is a
        yes/no judgment. `engine`: None/typed (decision models), "generative" (local
        LLM adjudicator, uncalibrated), or "auto" (typed, fall back to generative).
        Returns answer, confidence, and the trace.
        """
        return ask(cfg, state, question, choices=choices, engine=engine)

    return mcp


def run(cfg):
    build(cfg).run()