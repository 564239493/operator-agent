from pydantic import BaseModel

from shared.models.enums import DataFormat, DataType, ParamDirection


class ShapeConstraint(BaseModel):
    rank_range: tuple[int, int]
    rank_format_map: dict[int, DataFormat] | None = None
    channel_axis: int | None = None
    channel_axis_description: str | None = None
    supports_empty_tensor: bool = False


class DtypeConstraint(BaseModel):
    allowed_dtypes: list[DataType]
    must_match_param: str | None = None
    product_exclusions: dict[str, list[DataType]] | None = None


class CrossParamRule(BaseModel):
    description: str
    expression: str
    source_params: list[str]
    rule_type: str  # "shape_match" | "dtype_match" | "custom"


class ParameterConstraint(BaseModel):
    name: str
    direction: ParamDirection
    description: str
    dtype_constraint: DtypeConstraint
    shape_constraint: ShapeConstraint
    format_constraint: list[DataFormat]
    nullable: bool = False
    special_notes: list[str] = []


class ErrorCodeSpec(BaseModel):
    code: str
    error_number: int
    description: str
    trigger_conditions: list[str]


class ProductRule(BaseModel):
    products: list[str]
    constraint: str
    expression: str


class OperatorConstraint(BaseModel):
    operator_name: str
    api_version: str
    description: str
    formula: str | None = None
    two_stage_api: bool = False
    get_workspace_api: str | None = None
    execute_api: str | None = None
    parameters: list[ParameterConstraint] = []
    cross_param_rules: list[CrossParamRule] = []
    product_constraints: list[ProductRule] = []
    error_codes: list[ErrorCodeSpec] = []
    additional_constraints: list[str] = []
