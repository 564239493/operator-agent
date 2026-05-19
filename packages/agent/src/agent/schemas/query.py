from pydantic import BaseModel


class OperatorSummary(BaseModel):
    name: str
    source_url: str | None = None
    latest_version: int | None = None
    created_at: str | None = None


class OperatorListResponse(BaseModel):
    operators: list[OperatorSummary]


class OperatorDetailResponse(BaseModel):
    success: bool
    operator_name: str | None = None
    version: int | None = None
    parsed_data: dict | None = None
    error: str | None = None
