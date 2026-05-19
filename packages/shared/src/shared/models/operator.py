from typing import Any

from pydantic import BaseModel

from shared.models.enums import SectionType


class ProductSupport(BaseModel):
    product: str
    supported: bool


class FunctionSignature(BaseModel):
    return_type: str
    function_name: str
    parameters: list[str]
    raw_code: str


class ParsedSection(BaseModel):
    section_type: SectionType
    heading: str
    content: str
    line_start: int
    line_end: int
    metadata: dict[str, Any] = {}


class ParameterTableRow(BaseModel):
    cells: dict[str, str]


class ParsedOperatorDocument(BaseModel):
    operator_name: str
    cann_version: str
    source_url: str | None = None
    saved_date: str | None = None
    sections: list[ParsedSection]
    product_support: list[ProductSupport] = []
    function_signatures: list[FunctionSignature] = []
