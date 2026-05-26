"""ParamDescExtract node: extract parameter descriptions via LLM and update DB."""

import asyncio
import logging
import re
from typing import Any

from langchain_openai import ChatOpenAI

from agent.core.config import settings
from agent.mcp_client import MCPClient
from agent.nodes.state import PipelineState
from agent.prompts import PARAM_DESC_EXTRACT_PROMPT

logger = logging.getLogger(__name__)

_mcp_client = MCPClient()

_CONCURRENCY_LIMIT = 5

_DIRECTION_RE = re.compile(r"\|\s*输入\s*/\s*输出\s*\|\s*(输入|输出)\s*\|")


def _parse_direction(desc: str) -> str:
    """Extract direction from the LLM-generated markdown table.

    Matches rows like ``| 输入/输出 | 输入 |`` or ``| 输入/输出 | 输出 |``
    and maps them to ``"input"`` / ``"output"``.
    """
    m = _DIRECTION_RE.search(desc)
    if not m:
        return ""
    return "input" if m.group(1) == "输入" else "output"


async def param_desc_extract_node(state: PipelineState) -> dict[str, Any]:
    """Extract detailed descriptions for each parameter via LLM and update DB.

    Flow:
    1. Query parameters by doc_id via MCP
    2. Fetch both params_get_workspace and params_execute section content
    3. Route GetWorkspaceSize parameters → params_get_workspace content,
       Execute parameters → params_execute content
    4. If the required section is missing, skip those parameters with a warning
    5. Call LLM concurrently (limit 5) for each parameter to extract description
    6. Batch update descriptions via MCP
    """
    doc_id = state.get("doc_id", 0)
    operator_name = state.get("operator_name", "")

    logger.info("ParamDescExtract: received state doc_id=%s for %s", doc_id, operator_name)

    if not doc_id:
        logger.warning("ParamDescExtract: no doc_id in state, skipping")
        return {"error": None}

    try:
        params = await _mcp_client.query_params_by_doc_id(doc_id)
        if not params:
            logger.info("ParamDescExtract: no parameters for doc_id=%s, skipping", doc_id)
            return {"error": None}

        # Get both section types: GetWorkspaceSize and Execute
        ws_section = await _mcp_client.get_section(doc_id, "params_get_workspace")
        ws_content = ws_section.get("content", "") if ws_section else ""

        exe_section = await _mcp_client.get_section(doc_id, "params_execute")
        exe_content = exe_section.get("content", "") if exe_section else ""

        # Split parameters by function type
        ws_params = [p for p in params if p.get("function_name", "").endswith("GetWorkspaceSize")]
        exe_params = [p for p in params if not p.get("function_name", "").endswith("GetWorkspaceSize")]

        llm = _create_llm()
        sem = asyncio.Semaphore(_CONCURRENCY_LIMIT)

        async def _extract_one(param: dict, content: str) -> dict:
            async with sem:
                desc = await _extract_desc(llm, param["param_name"], content)
                direction = _parse_direction(desc)
                return {
                    "function_name": param["function_name"],
                    "param_name": param["param_name"],
                    "direction": direction,
                    "description": desc,
                    "usage_notes": "",
                    "data_type": "",
                    "data_format": "",
                    "shape": "",
                    "memory_desc": "",
                }

        all_updates: list[dict] = []

        # Process GetWorkspaceSize function parameters
        if ws_params:
            if ws_content:
                updates = await asyncio.gather(*[_extract_one(p, ws_content) for p in ws_params])
                all_updates.extend(u for u in updates if u["description"])
            else:
                logger.warning(
                    "ParamDescExtract: params_get_workspace section not found for doc_id=%s, "
                    "skipping %d GetWorkspaceSize parameters",
                    doc_id, len(ws_params),
                )

        # Process Execute function parameters
        if exe_params:
            if exe_content:
                updates = await asyncio.gather(*[_extract_one(p, exe_content) for p in exe_params])
                all_updates.extend(u for u in updates if u["description"])
            else:
                logger.warning(
                    "ParamDescExtract: params_execute section not found for doc_id=%s, "
                    "skipping %d Execute parameters",
                    doc_id, len(exe_params),
                )

        if all_updates:
            result = await _mcp_client.update_param_descriptions(doc_id, all_updates)
            logger.info(
                "ParamDescExtract: updated %d/%d parameters for doc_id=%s",
                result.get("updated", 0),
                len(params),
                doc_id,
            )
        else:
            logger.info("ParamDescExtract: no descriptions extracted for doc_id=%s", doc_id)

        return {"error": None}

    except Exception as e:
        logger.exception("ParamDescExtract failed for %s", operator_name)
        return {"error": str(e)}


def _create_llm() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=settings.active_api_key,
        base_url=settings.active_base_url,
        model=settings.active_model,
        temperature=0.1,
    )


async def _extract_desc(llm: ChatOpenAI, param_name: str, content: str) -> str:
    """Call LLM to extract description for a single parameter."""
    prompt = PARAM_DESC_EXTRACT_PROMPT.format(param_name=param_name, content=content)
    response = await llm.ainvoke(prompt)
    text = response.content if hasattr(response, "content") else str(response)
    return text.strip()
