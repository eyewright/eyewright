"""eyewright mcp - eyewright as MCP tools for any AI harness.

Tools:
  eyewright_gate(state, question)                    -> three-eye gate: p_done + decision + trace
  eyewright_ask(state, question, choices?, levels?)  -> typed decision (yes/no, choice, or scale)

Run as a stdio MCP server: ``eyewright mcp`` (the ``mcp`` package is in the
default ``runtime`` dependency group; published installs use ``eyewright[mcp]``).
"""

from mcp.server.mcpserver import MCPServer

from .decide import ask
from .gate import decide_gate


def build(cfg):
    mcp = MCPServer("eyewright")

    @mcp.tool()
    def eyewright_gate(state: str, question: str) -> dict:
        """Gate a claim against the eyewright committee.

        Returns p_done, the policy decision (accept / consensus-* / review-*),
        and the full consult trace.
        """
        p, trace = decide_gate(cfg, state, question)
        return {"p_done": round(p, 4), "decision": trace.get("decision"), "trace": trace}

    @mcp.tool()
    def eyewright_ask(
        state: str,
        question: str,
        choices: dict | None = None,
        levels: list | None = None,
        engine: str | None = None,
    ) -> dict:
        """Ask eyewright a typed decision.

        Three shapes, same call:
          - neither `choices` nor `levels`: a yes/no judgment;
          - `choices` (option -> description): pick one option;
          - `levels` (ordered list of scale labels): rate on that scale.

        `engine`: None/typed (decision models), "generative" (local LLM
        adjudicator, uncalibrated), or "auto" (typed, fall back to generative).
        Returns answer, confidence, and the trace.
        """
        return ask(cfg, state, question, choices=choices, levels=levels, engine=engine)

    return mcp


def run(cfg):
    build(cfg).run()