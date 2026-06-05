"""Task routes: list docs, create tasks, query tasks."""

from __future__ import annotations

import asyncio
import logging
import re
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Query

from agent.core.config import settings
from agent.mcp_client import MCPClient
from agent.schemas.task import (
    CreateTaskRequest,
    CreateTaskResponse,
    TaskDetailResponse,
    TaskDocItem,
    TaskDocsResponse,
    TaskItemDetail,
    TaskListResponse,
    TaskSummary,
)
from agent.services.task_engine import run_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["task"])

_mcp_client = MCPClient()


@router.get("/task-docs", response_model=TaskDocsResponse)
async def list_task_docs(search: str | None = Query(default=None)) -> TaskDocsResponse:
    """Scan operators/ directory and return all .md files."""
    ops_dir = Path(settings.operators_dir)
    if not ops_dir.exists():
        return TaskDocsResponse(documents=[], total=0)

    docs: list[TaskDocItem] = []
    for md_file in sorted(ops_dir.rglob("*.md")):
        name = md_file.stem
        if search and search.lower() not in name.lower():
            continue
        rel_path = str(md_file.relative_to(ops_dir.parent))
        # category = parent dir relative to operators/, or "" if in root
        parts = md_file.relative_to(ops_dir).parts
        category = parts[0] if len(parts) > 1 else ""
        docs.append(
            TaskDocItem(
                name=name,
                path=rel_path,
                size=md_file.stat().st_size,
                category=category,
            )
        )

    return TaskDocsResponse(documents=docs, total=len(docs))


@router.post("/tasks", response_model=CreateTaskResponse)
async def create_task(req: CreateTaskRequest) -> CreateTaskResponse:
    """Create a new batch task, copy files, and start background execution."""
    if not req.file_paths:
        return CreateTaskResponse(success=False, error="file_paths is empty")

    # Generate timestamp directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    upload_dir_name = f"uploads/{timestamp}"
    upload_dir = Path(upload_dir_name)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate task name
    task_name = req.name or f"batch-{timestamp}"

    # Copy files
    ops_base = Path(settings.operators_dir).parent  # project root
    for fp in req.file_paths:
        src = ops_base / fp
        if not src.exists():
            logger.warning("File not found: %s", src)
            continue
        dst = upload_dir / src.name
        shutil.copy2(str(src), str(dst))

    # Extract operator names from filenames
    items = []
    for seq, fp in enumerate(req.file_paths, start=1):
        src = ops_base / fp
        if not src.exists():
            continue
        operator_name = _extract_operator_name(src)
        items.append(
            {
                "seq": seq,
                "operator_name": operator_name,
                "file_path": str(upload_dir / src.name),
            }
        )

    if not items:
        return CreateTaskResponse(success=False, error="No valid files found")

    try:
        # Create task in DB
        result = await _mcp_client.create_task(task_name, len(items), upload_dir_name)
        task_id = result["task_id"]

        # Create task items
        await _mcp_client.create_task_items(task_id, items)

        # Start background execution
        asyncio.create_task(run_task(task_id))

        return CreateTaskResponse(
            success=True,
            task_id=task_id,
            name=task_name,
            total_count=len(items),
            upload_dir=upload_dir_name,
            status="pending",
        )

    except Exception as e:
        logger.exception("Failed to create task")
        return CreateTaskResponse(success=False, error=str(e))


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks() -> TaskListResponse:
    """List all tasks."""
    try:
        result = await _mcp_client.list_tasks()
        tasks = [
            TaskSummary(
                id=t["id"],
                name=t["name"],
                status=t["status"],
                total_count=t["total_count"],
                completed_count=t["completed_count"],
                failed_count=t["failed_count"],
                created_at=t.get("created_at"),
                updated_at=t.get("updated_at"),
            )
            for t in result
        ]
        return TaskListResponse(tasks=tasks)
    except Exception:
        return TaskListResponse(tasks=[])


@router.get("/tasks/{task_id}", response_model=TaskDetailResponse)
async def get_task_detail(task_id: int) -> TaskDetailResponse:
    """Get task detail with all items."""
    result = await _mcp_client.get_task_with_items(task_id)
    if result is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Task not found")

    items = [
        TaskItemDetail(
            id=item["id"],
            seq=item["seq"],
            operator_name=item["operator_name"],
            file_path=item["file_path"],
            status=item["status"],
            doc_id=item.get("doc_id"),
            error=item.get("error"),
            started_at=item.get("started_at"),
            finished_at=item.get("finished_at"),
        )
        for item in result.get("items", [])
    ]

    return TaskDetailResponse(
        id=result["id"],
        name=result["name"],
        status=result["status"],
        total_count=result["total_count"],
        completed_count=result["completed_count"],
        failed_count=result["failed_count"],
        upload_dir=result["upload_dir"],
        created_at=result.get("created_at"),
        updated_at=result.get("updated_at"),
        items=items,
    )


def _extract_operator_name(file_path: Path) -> str:
    """Extract operator name from filename (stem).

    E.g. aclnnAddRmsNorm.md -> aclnnAddRmsNorm
    """
    stem = file_path.stem
    # Try to read the file and extract from H1 heading
    try:
        content = file_path.read_text(encoding="utf-8")
        for line in content.split("\n"):
            m = re.match(r"^#{1,2}\s+(.+?)-CANN社区版", line)
            if m:
                return m.group(1).strip()
            m = re.match(r"^#{1,2}\s+(aclnn?\w+)", line)
            if m:
                return m.group(1).strip()
    except Exception:
        pass
    return stem
