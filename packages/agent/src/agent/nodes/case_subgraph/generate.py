"""Step 5 of GeneratorAgent: generate the test case data.

Wraps the existing ``TestCaseGenerator``: parses the constraints, runs the
sampler to produce ``count`` cases, and persists them to the DB + disk via MCP.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from agent.generators import TestCaseGenerator, parse_result_json
from agent.mcp_client import MCPClient
from agent.nodes.state import PipelineState

logger = logging.getLogger(__name__)

_mcp_client = MCPClient()

_DEFAULT_COUNT = 10
_DEFAULT_SEED = 42


async def case_generate_node(state: PipelineState) -> dict[str, Any]:
    """Run the TestCaseGenerator and persist results to MCP + disk."""
    if state.get("error"):
        return {"error": state.get("error")}

    operator_name = state.get("operator_name", "")
    constraints = state.get("constraints_raw")
    if not operator_name or not constraints:
        return {"error": "operator_name or constraints_raw missing"}

    count = int(state.get("cases_count") or state.get("count") or _DEFAULT_COUNT)
    seed = int(state.get("cases_seed") or state.get("seed") or _DEFAULT_SEED)

    logger.info(
        "case_generate: running TestCaseGenerator for %s (count=%d, seed=%d)",
        operator_name, count, seed,
    )

    try:
        context = parse_result_json(constraints)
        cases = TestCaseGenerator(context, seed=seed).generate(count=count)
        cases_json = json.dumps(
            [c.model_dump() for c in cases], ensure_ascii=False,
        )
        save_result = await _mcp_client.save_test_cases(
            operator_name=operator_name,
            cases_json=cases_json,
            source="generated",
        )
        out_path = save_result.get("output_path", "")
        logger.info(
            "case_generate: %s → %d cases at %s",
            operator_name, len(cases), out_path,
        )
        return {
            "cases": [c.model_dump() for c in cases],
            "cases_path": out_path,
            "cases_count": len(cases),
            "error": None,
        }
    except Exception as e:
        logger.exception("case_generate failed for %s", operator_name)
        return {"error": str(e), "cases_path": None, "cases_count": None}
