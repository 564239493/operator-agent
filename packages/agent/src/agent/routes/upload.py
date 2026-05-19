"""Upload route: accepts operator documents and triggers processing via MCP."""

from __future__ import annotations

import hashlib
import logging
import re

from fastapi import APIRouter, UploadFile

from agent.mcp_client import MCPClient
from agent.schemas.upload import UploadResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["upload"])

_mcp_client = MCPClient()


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile) -> UploadResponse:
    """Upload a CANN operator Markdown document for processing.

    Flow:
    1. Read file content, compute hash
    2. Call MCP: check_version → determine if new/unchanged/updated
    3. If unchanged → return existing parsed data
    4. If new/updated → save to DB, parse, return result
    """
    content = (await file.read()).decode("utf-8")
    filename = file.filename or "unknown"

    # Step 1: Quick pre-parse to extract operator_name (from H1 title)
    # We do this locally to avoid an MCP round-trip just for the name
    operator_name = _extract_operator_name(content)
    if not operator_name:
        return UploadResponse(success=False, error=f"Cannot parse operator name from {filename}")

    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    client = _mcp_client

    try:
        # Step 2: Check version via MCP
        version_info = await client.check_version(operator_name, content_hash)
        status = version_info.get("status", "new")
        existing_version = version_info.get("version")

        # Step 3: If unchanged, return existing data
        if status == "unchanged":
            existing = await client.get_parsed(operator_name, existing_version)
            if existing:
                return UploadResponse(
                    success=True,
                    operator_name=operator_name,
                    cann_version=existing.get("cann_version"),
                    status="unchanged",
                    version=existing_version,
                    sections_count=len(existing.get("sections", [])),
                )

        # Step 4: Save new/updated document
        save_result = await client.save_doc(operator_name, content)
        new_version = save_result["version"]

        # Step 5: Parse via MCP
        parsed = await client.parse_doc(content)

        # Step 6: Save parsed result
        await client.save_parsed(operator_name, new_version, parsed)

        return UploadResponse(
            success=True,
            operator_name=parsed.get("operator_name"),
            cann_version=parsed.get("cann_version"),
            status=status,
            version=new_version,
            sections_count=len(parsed.get("sections", [])),
        )

    except Exception as e:
        logger.exception("Upload processing failed for %s", filename)
        return UploadResponse(success=False, error=str(e))


def _extract_operator_name(content: str) -> str | None:
    """Extract operator name from the H1 title line.

    Format: # {name}-CANN社区版{version}-昇腾社区
    """
    for line in content.split("\n"):
        m = re.match(r"^#\s+(.+?)-CANN社区版", line)
        if m:
            return m.group(1).strip()
    return None
