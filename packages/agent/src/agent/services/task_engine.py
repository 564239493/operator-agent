"""Background task execution engine for batch operator document processing."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from agent.graph import create_pipeline_graph
from agent.mcp_client import MCPClient

logger = logging.getLogger(__name__)

# Global lock: only one task runs at a time to avoid LLM concurrency limits
_run_lock = asyncio.Lock()


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


async def run_task(task_id: int) -> None:
    """Execute all pending items in a task sequentially.

    Acquires a global lock to ensure only one task runs at a time.
    For each pending item:
    1. Set item status to 'running'
    2. Read file content and compute hash
    3. Invoke the pipeline graph
    4. Set item status to 'completed' or 'failed'
    5. Refresh task progress
    After all items, set task status to 'completed' or 'failed'.
    """
    async with _run_lock:
        mcp = MCPClient()
        graph = create_pipeline_graph()

        # Set task to running
        await mcp.update_task_status(task_id, "running")

        # Get all pending items
        items = await mcp.get_pending_task_items(task_id)

        for item in items:
            item_id = item["id"]
            file_path = item["file_path"]
            operator_name = item["operator_name"]

            # Set item to running
            await mcp.update_task_item_status(
                item_id, "running", started_at=_now_iso()
            )

            try:
                # Read file content
                content = Path(file_path).read_text(encoding="utf-8")
                content_hash = hashlib.sha256(
                    content.encode("utf-8")
                ).hexdigest()

                # Execute pipeline
                result = await graph.ainvoke(
                    {
                        "operator_name": operator_name,
                        "content": content,
                        "content_hash": content_hash,
                    }
                )

                pipeline_error = result.get("error")
                if pipeline_error:
                    await mcp.update_task_item_status(
                        item_id,
                        "failed",
                        error=pipeline_error,
                        doc_id=result.get("doc_id"),
                        finished_at=_now_iso(),
                    )
                else:
                    await mcp.update_task_item_status(
                        item_id,
                        "completed",
                        doc_id=result.get("doc_id"),
                        finished_at=_now_iso(),
                    )

            except Exception as e:
                logger.exception("Task item %s failed: %s", item_id, e)
                await mcp.update_task_item_status(
                    item_id,
                    "failed",
                    error=str(e),
                    finished_at=_now_iso(),
                )

            # Refresh task progress
            await mcp.refresh_task_progress(task_id)

        # Set final task status
        task = await mcp.get_task(task_id)
        if task is None:
            logger.error("Task %s not found after execution", task_id)
            return

        final_status = "completed" if task["failed_count"] == 0 else "failed"
        await mcp.update_task_status(task_id, final_status)
        logger.info(
            "Task %s finished: %s (completed=%d, failed=%d)",
            task_id,
            final_status,
            task["completed_count"],
            task["failed_count"],
        )
