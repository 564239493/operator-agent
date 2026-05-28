"""ShapeExtract node: extract unconditional shape values from parameter descriptions via LLM."""

import asyncio
import json
import logging
import re
from typing import Any

from langchain_openai import ChatOpenAI

from agent.core.config import settings
from agent.mcp_client import MCPClient
from agent.nodes.state import PipelineState
from agent.prompts import SHAPE_EXTRACT_PROMPT

logger = logging.getLogger(__name__)

_mcp_client = MCPClient()

_CONCURRENCY_LIMIT = 5
_MAX_PARAMS_PER_BATCH = 15

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


async def shape_extract_node(state: PipelineState) -> dict[str, Any]:
    """Extract unconditional shape values from parameter descriptions and persist to DB.

    Flow:
    1. Query parameters by doc_id via MCP
    2. Filter to parameters with non-empty descriptions
    3. Group by function_name, batch each group to one LLM call
    4. LLM extracts unconditional shape values (ignoring conditional ones)
    5. Batch update shape field via MCP
    """
    doc_id = state.get("doc_id", 0)
    operator_name = state.get("operator_name", "")

    logger.info("ShapeExtract: received state doc_id=%s for %s", doc_id, operator_name)

    if not doc_id:
        logger.warning("ShapeExtract: no doc_id in state, skipping")
        return {"error": None}

    try:
        params = await _mcp_client.query_params_by_doc_id(doc_id)
        if not params:
            logger.info("ShapeExtract: no parameters for doc_id=%s, skipping", doc_id)
            return {"error": None}

        # Only process parameters that have a description to extract shape from
        described = [p for p in params if p.get("description")]
        if not described:
            logger.info("ShapeExtract: no parameters with descriptions for doc_id=%s, skipping", doc_id)
            return {"error": None}

        # Group by function_name for batched LLM calls
        groups: dict[str, list[dict]] = {}
        for p in described:
            fn = p.get("function_name", "")
            groups.setdefault(fn, []).append(p)

        llm = _create_llm()
        sem = asyncio.Semaphore(_CONCURRENCY_LIMIT)

        async def _extract_group(fn_name: str, group_params: list[dict]) -> list[dict]:
            async with sem:
                return await _extract_shapes(llm, fn_name, group_params)

        # Process all groups concurrently
        group_results = await asyncio.gather(
            *[_extract_group(fn, g) for fn, g in groups.items()]
        )

        all_updates: list[dict] = []
        for result in group_results:
            all_updates.extend(result)

        # Only keep updates with non-empty shape
        shape_updates = [u for u in all_updates if u.get("shape")]
        if shape_updates:
            result = await _mcp_client.update_param_shape(doc_id, shape_updates)
            logger.info(
                "ShapeExtract: updated shape for %d/%d parameters (doc_id=%s)",
                result.get("updated", 0),
                len(described),
                doc_id,
            )
        else:
            logger.info("ShapeExtract: no unconditional shapes extracted for doc_id=%s", doc_id)

        return {"error": None}

    except Exception as e:
        logger.exception("ShapeExtract failed for %s", operator_name)
        return {"error": str(e)}


def _create_llm() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=settings.active_api_key,
        base_url=settings.active_base_url,
        model=settings.active_model,
        temperature=0.1,
    )


async def _extract_shapes(
    llm: ChatOpenAI, function_name: str, params: list[dict]
) -> list[dict]:
    """Call LLM to extract unconditional shape values for a group of parameters.

    Returns a list of dicts with function_name, param_name, and shape keys.
    """
    # Build params_text: each parameter's name and its markdown description
    entries = []
    for p in params:
        entries.append(f"--- 参数: {p['param_name']} ---\n{p['description']}")
    params_text = "\n\n".join(entries)

    prompt = SHAPE_EXTRACT_PROMPT.format(params_text=params_text)
    response = await llm.ainvoke(prompt)
    text = response.content if hasattr(response, "content") else str(response)

    extracted = _parse_shape_response(text)

    # Attach function_name to each result
    for item in extracted:
        item["function_name"] = function_name
    return extracted


def _parse_shape_response(text: str) -> list[dict]:
    """Parse LLM JSON response into list of {param_name, shape} dicts."""
    # Strip markdown code blocks
    match = _JSON_BLOCK_RE.search(text)
    if match:
        text = match.group(1)
    text = text.strip()

    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Try to find JSON array anywhere in the text
    array_match = re.search(r"\[[\s\S]*\]", text)
    if array_match:
        try:
            data = json.loads(array_match.group(0))
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    logger.warning("ShapeExtract: failed to parse LLM response as JSON: %s", text[:200])
    return []
