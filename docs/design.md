# Operator Agent 设计文档

> 版本: v0.2 | 日期: 2026-05-14

## 1. 项目定位

基于 LangGraph + MCP 构建的智能体，核心业务流程：

```
算子文档(Markdown) → 语义解析 → 约束提取(人工审核) → Python 约束表达式 → Python 测试用例生成
```

目标：自动理解 CANN 算子文档，语义化提取参数约束（shape / format / dtype / 跨参数关系），经人工审核确认后，输出结构化的 Python 约束模型，并据此生成可执行的 Python 测试用例文件。

---

## 2. 核心概念

### 2.1 约束（Constraint）

从算子文档中提取的每一条参数限制，例如：

| 来源文本 | 提取的约束类型 | Python 表达式示例 |
|---------|-------------|-----------------|
| "支持的shape和格式有：2维（NC），3维（NCL），4维（NCHW）" | Shape + Format 映射 | `input.rank in {2,3,4,5,6,7,8}` 且 `rank_to_format = {2:NC, 3:NCL, 4:NCHW, 5:NCDHW, (6,7,8):ND}` |
| "数据类型与 input 的数据类型保持一致" | 跨参数类型约束 | `weight.dtype == input.dtype` |
| "shape长度与 input 中 channel 轴的长度相等" | 跨参数 shape 约束 | `weight.shape == [input.shape[1]]` |
| "Atlas 训练系列产品不支持 BFLOAT16" | 产品-类型约束 | `if product in {Atlas_Training, Atlas_Inference}: dtype not in {BFLOAT16}` |
| "支持空 Tensor" | 空值语义 | `input.nullable == True` |

### 2.2 约束模型（Constraint Model）

一个算子的全部约束，组织为结构化的 Pydantic 模型：

```python
class OperatorConstraint(BaseModel):
    operator_name: str                          # e.g. "aclnnBatchNormElemt"
    api_version: str                            # e.g. "CANN 9.0.0"
    parameters: list[ParameterConstraint]       # 每个参数的独立约束
    cross_param_rules: list[CrossParamRule]      # 跨参数约束
    product_constraints: list[ProductRule]       # 产品-特性约束
    error_codes: list[ErrorCodeSpec]            # 错误码规范
```

### 2.3 测试用例（Test Case）

基于约束模型，生成符合/违反约束的 Python 测试数据：

```python
# 正向用例：满足所有约束
TestCase(
    name="basic_4d_float32",
    inputs={"input": TensorSpec(shape=[2,4,3,3], dtype=FLOAT32, format=NCHW), ...},
    expected_status="ACL_SUCCESS"
)

# 反向用例：故意违反某条约束
TestCase(
    name="dtype_mismatch_weight",
    inputs={"input": TensorSpec(dtype=FLOAT32), "weight": TensorSpec(dtype=FLOAT16)},
    expected_status="ACLNN_ERR_PARAM_INVALID",
    violated_constraint="input.dtype == weight.dtype"
)
```

### 2.4 文档版本管理

算子文档支持版本追踪，当文档更新时：

```
v1.0 文档 ──→ 完整约束提取 ──→ Constraint v1.0
                                        │
v1.1 文档 ──→ diff v1.0 vs v1.1 ──→ 变更段识别 ──→ 增量约束提取 ──→ Constraint v1.1
```

- 每次文档入库自动记录版本号（递增）
- 检测到新版本时，对比前后差异，仅对变更段落重新提取约束
- 已确认的约束如未受影响，保持原状不重复提取

---

## 3. 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                     FastAPI Application                       │
│  /api/v1/ ...                                                │
│  后台任务：启动/管理多个 LangGraph 实例                         │
└──────────────┬───────────────────────────────────┬───────────┘
               │                                   │
               ▼                                   ▼
┌───────────────────────────┐   ┌──────────────────────────────┐
│      MCP Server (DB)      │   │     LangGraph Agent           │
│  (FastMCP / stdio|http)   │   │                               │
│                           │   │  ┌─────┐                      │
│  Tools:                   │   │  │Entry│                      │
│  ─ 数据库 CRUD            │   │  └──┬──┘                      │
│  ─ 文档版本管理           │   │     │                          │
│  ─ 约束持久化             │   │     ▼                          │
│  ─ 测试用例存储           │   │  ┌─────────────────────┐     │
│                           │   │  │  Node Pipeline       │     │
│  项目不直接连接 DB,       │   │  │  doc_loader          │     │
│  全部通过 MCP Tool 访问   │   │  │  doc_parser          │     │
│                           │   │  │  constraint_extractor│     │
│  Resources:               │   │  │  constraint_validator│     │
│  ─ operator://list        │   │  │  human_review  ◄────┼─ 人工│
│  ─ operator://{name}      │   │  │  expr_generator      │     │
│  ─ operator://{name}/ver  │   │  │  test_planner        │     │
│  ─ operator://{name}/tests│   │  │  test_generator      │     │
│                           │   │  │  codegen             │     │
│  Prompts:                 │   │  │  final_validator     │     │
│  ─ extract_prompt         │   │  └─────────────────────┘     │
│  ─ test_gen_prompt        │   │                               │
│  ─ validate_prompt        │   │  节点内通过 @Tool 调用       │
│                           │   │  MCP Server 的数据库工具     │
└───────────┬───────────────┘   └───────────┬──────────────────┘
            │                                │
            │    ┌───────────────────────┐   │
            │    │   SQLite Database     │   │
            │    │   (通过 MCP 独占访问)  │◄──┘
            │    └───────────────────────┘
            │
            ▼
┌──────────────────────────────────────────────────────────────┐
│                     Service Layer                             │
│  DocumentService | ConstraintService | TestCaseService        │
│  VersionService | LLMRouter | PromptManager                  │
└──────────────────────────┬───────────────────────────────────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
┌────────────────┐ ┌──────────────┐ ┌──────────────┐
│  LLM Providers │ │  Templates   │ │   Files      │
│  OpenAI/Claude │ │  Jinja2      │ │  Markdown    │
│  /通义/文心    │ │  (Python)    │ │  Docs        │
└────────────────┘ └──────────────┘ └──────────────┘
```

### 3.1 数据库访问架构

**核心原则：项目不直接连接数据库，所有 DB 操作通过 MCP Tool 完成。**

```
LangGraph Node / Service
       │
       │ 调用 @Tool
       ▼
MCP Server (DB Tools)
       │
       │ SQLite 操作
       ▼
SQLite Database
```

MCP Server 是数据库的唯一入口，负责：
- 算子文档的 CRUD + 版本管理
- 约束模型的存取
- 测试用例的存取
- 流程状态的追踪

---

## 4. LangGraph 工作流设计

### 4.1 主图（Main Graph）

```python
class AgentState(TypedDict):
    # 输入
    operator_name: str                       # 算子名称
    document_path: str                       # 文档路径

    # 文档处理
    raw_document: str                        # 文档原始 Markdown
    document_version: int                    # 文档版本号
    parsed_sections: ParsedSections          # 解析后的文档分节
    changed_sections: list[str] | None       # 增量变更的段落（版本更新时）

    # 约束提取
    constraints: OperatorConstraint          # 提取的约束模型
    constraint_version: int                  # 约束版本号
    constraint_expressions: list[str]        # Python 约束表达式

    # 人工审核
    review_status: str                       # "pending" | "approved" | "rejected"
    review_comments: list[str]               # 审核意见
    revision_count: int                      # 修订次数

    # 测试生成
    test_plan: TestPlan                      # 测试规划
    test_cases: list[TestCase]               # 测试用例列表
    test_file_content: str                   # 生成的 Python 测试文件代码
    validation_result: ValidationResult      # 最终校验结果

    # 流程控制
    errors: list[str]                        # 错误信息
    current_step: str                        # 当前步骤标识
```

### 4.2 节点定义

| 节点 | 输入 | 输出 | LLM | 说明 |
|------|------|------|-----|------|
| **doc_loader** | document_path | raw_document, document_version | -- | 读取 Markdown；通过 MCP Tool 查询/创建文档版本记录 |
| **doc_parser** | raw_document | parsed_sections | LOW | 按结构拆分：产品支持 / 函数原型 / 参数表 / 约束 / 示例代码 |
| **version_differ** | parsed_sections, document_version | changed_sections | -- | 新版本时 diff 变更段落；首版则标记全量提取 |
| **constraint_extractor** | parsed_sections, changed_sections | constraints | HIGH | LLM 语义提取：dtype、shape、format、跨参数关系、产品约束 |
| **constraint_validator** | constraints | constraints (修正) | HIGH | LLM 自纠错：检查一致性、遗漏、矛盾；最多 3 轮 |
| **human_review** | constraints | review_status, review_comments | -- | **人工审核节点**：暂停图执行，等待人工确认/打回 |
| **expr_generator** | constraints | constraint_expressions | MEDIUM | 将约束转化为 Python 表达式 / 可执行断言 |
| **test_planner** | constraints, constraint_expressions | test_plan | MEDIUM | 规划正向/反向/边界用例组合策略 |
| **test_generator** | test_plan, constraint_expressions | test_cases | MEDIUM | 生成具体测试用例（含 TensorSpec 数据） |
| **codegen** | test_cases, constraints | test_file_content | LOW | 基于 Jinja2 模板生成 Python 测试文件 |
| **final_validator** | test_file_content | validation_result | -- | Python 语法检查 + 约束覆盖率校验 |
| **result_persister** | test_file_content, constraints, validation_result | -- | -- | 通过 MCP Tool 将最终结果写入数据库 |

### 4.3 图拓扑

```
                    ┌──────────────┐
                    │  doc_loader   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  doc_parser   │
                    └──────┬───────┘
                           │
                    ┌──────▼────────┐
                    │ version_differ │──── 新版本: changed_sections
                    └──────┬────────┘      首版本: None (全量)
                           │
              ┌────────────▼─────────────┐
              │  constraint_extractor     │
              └────────────┬─────────────┘
                           │
                  ┌────────▼─────────┐
              ┌───│constraint_valid. │◄── 自纠错循环 (max 3)
              │   └────────┬─────────┘
              │ error       │ pass
              │             │
              │     ┌───────▼────────┐
              │     │  human_review   │◄──────────────────────┐
              │     └───────┬────────┘                        │
              │             │                                  │
              │     ┌───────▼────────┐                        │
              │     │ (approved?)    │── rejected ──→ 修改约束 │
              │     └───────┬────────┘            + comments  │
              │             │ approved                         │
              │     ┌───────▼──────────┐                      │
              │     │  expr_generator   │                      │
              │     └───────┬──────────┘                      │
              │             │                                  │
              │     ┌───────▼──────────┐                      │
              │     │  test_planner     │                      │
              │     └───────┬──────────┘                      │
              │             │                                  │
              │     ┌───────▼──────────┐                      │
              │     │  test_generator   │                      │
              │     └───────┬──────────┘                      │
              │             │                                  │
              │     ┌───────▼──────────┐                      │
              │     │  codegen          │                      │
              │     └───────┬──────────┘                      │
              │             │                                  │
              │     ┌───────▼──────────┐                      │
              │     │  final_validator  │                      │
              │     └───────┬──────────┘                      │
              │             │                                  │
              │     ┌───────▼──────────┐                      │
              │     │ result_persister  │                      │
              │     └───────┬──────────┘                      │
              │             │                                  │
              └── error     ▼                                  │
                       [END] ◄─────────────────────────────────┘
                       (如果 rejected, 回到 human_review 重新审核)
```

### 4.4 人工审核机制（Human-in-the-loop）

LangGraph 的 `interrupt` 机制实现：

```python
# human_review 节点伪代码
def human_review(state: AgentState) -> dict:
    # 将约束模型持久化到 DB（通过 MCP Tool）
    save_constraints_for_review(state.constraints)

    # 暂停图执行，等待外部信号
    return {"review_status": "pending"}

# 图恢复时，从 DB 读取审核结果（通过 MCP Tool）
def should_proceed_after_review(state: AgentState) -> str:
    if state.review_status == "approved":
        return "expr_generator"
    elif state.review_status == "rejected":
        return "constraint_extractor"  # 带着审核意见重新提取
    else:
        return "human_review"          # 继续等待
```

审核 API：
- `POST /api/v1/review/{operator_name}/approve` — 通过
- `POST /api/v1/review/{operator_name}/reject` — 打回（附审核意见）
- `GET  /api/v1/review/{operator_name}/pending` — 查看待审核列表

---

## 5. 数据模型设计

### 5.1 参数约束模型

```python
from enum import Enum
from pydantic import BaseModel, Field

class DataType(str, Enum):
    FLOAT32 = "FLOAT32"
    FLOAT16 = "FLOAT16"
    BFLOAT16 = "BFLOAT16"
    INT32 = "INT32"
    INT64 = "INT64"
    INT8 = "INT8"
    UINT8 = "UINT8"
    BOOL = "BOOL"

class DataFormat(str, Enum):
    ND = "ND"
    NC = "NC"
    NCL = "NCL"
    NCHW = "NCHW"
    NCDHW = "NCDHW"
    NHWC = "NHWC"

class ParamDirection(str, Enum):
    INPUT = "input"
    OUTPUT = "output"

class ShapeConstraint(BaseModel):
    """单个参数的 shape 约束"""
    rank_range: tuple[int, int]                              # e.g. (2, 8)
    rank_format_map: dict[int, DataFormat] | None = None     # {2: NC, 3: NCL, ...}
    channel_axis: int | None = None                          # channel 轴位置
    channel_axis_description: str | None = None
    supports_empty_tensor: bool = False

class DtypeConstraint(BaseModel):
    """数据类型约束"""
    allowed_dtypes: list[DataType]
    must_match_param: str | None = None                      # e.g. "input"
    product_exclusions: dict[str, list[DataType]] | None = None

class CrossParamRule(BaseModel):
    """跨参数约束"""
    description: str
    expression: str                      # e.g. "weight.shape == [input.shape[1]]"
    source_params: list[str]
    rule_type: str                       # "shape_match" | "dtype_match" | "custom"

class ParameterConstraint(BaseModel):
    """单个参数的全部约束"""
    name: str
    direction: ParamDirection
    description: str
    dtype_constraint: DtypeConstraint
    shape_constraint: ShapeConstraint
    format_constraint: list[DataFormat]
    nullable: bool = False
    special_notes: list[str] = []

class ErrorCodeSpec(BaseModel):
    """错误码规范"""
    code: str
    error_number: int
    description: str
    trigger_conditions: list[str]

class ProductRule(BaseModel):
    """产品-特性约束"""
    products: list[str]
    constraint: str
    expression: str

class OperatorConstraint(BaseModel):
    """算子的完整约束模型"""
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
```

### 5.2 测试用例模型

```python
class TensorSpec(BaseModel):
    """测试中一个 Tensor 的具体规格"""
    shape: list[int]
    dtype: DataType
    format: DataFormat
    data_values: list[float] | None = None
    is_empty: bool = False

class TestCase(BaseModel):
    """单个测试用例"""
    name: str
    category: str                           # "positive" | "negative" | "boundary"
    description: str
    inputs: dict[str, TensorSpec]
    scalar_params: dict[str, float | int]   # 标量参数
    expected_status: str                    # ACL_SUCCESS 或错误码
    violated_constraint: str | None = None

class TestFile(BaseModel):
    """生成的完整 Python 测试文件"""
    operator_name: str
    imports: list[str]                      # import 语句
    helper_functions: list[str]             # 辅助函数
    test_cases: list[TestCase]
    generated_code: str                     # 最终 Python 代码
    constraint_coverage: dict[str, float]   # 约束覆盖率
```

### 5.3 数据库 Schema（SQLite）

```sql
-- 算子文档
CREATE TABLE operators (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,           -- e.g. "aclnnBatchNormElemt"
    source_url  TEXT,                           -- 文档来源 URL
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

-- 文档版本
CREATE TABLE document_versions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    operator_id     INTEGER NOT NULL REFERENCES operators(id),
    version         INTEGER NOT NULL DEFAULT 1,
    content         TEXT NOT NULL,               -- Markdown 原文
    content_hash    TEXT NOT NULL,               -- SHA256，用于变更检测
    change_summary  TEXT,                        -- 变更摘要
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(operator_id, version)
);

-- 约束模型
CREATE TABLE constraints (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    operator_id     INTEGER NOT NULL REFERENCES operators(id),
    doc_version     INTEGER NOT NULL,            -- 关联文档版本
    constraint_data TEXT NOT NULL,               -- JSON: OperatorConstraint
    status          TEXT NOT NULL DEFAULT 'draft',  -- draft/pending_review/approved/rejected
    review_comments TEXT,                        -- JSON: list[str]
    revision_count  INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

-- 约束表达式
CREATE TABLE constraint_expressions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    constraint_id   INTEGER NOT NULL REFERENCES constraints(id),
    expression      TEXT NOT NULL,               -- Python 表达式
    description     TEXT,                        -- 自然语言描述
    created_at      TEXT DEFAULT (datetime('now'))
);

-- 测试用例
CREATE TABLE test_cases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    constraint_id   INTEGER NOT NULL REFERENCES constraints(id),
    name            TEXT NOT NULL,
    category        TEXT NOT NULL,               -- positive/negative/boundary
    test_data       TEXT NOT NULL,               -- JSON: TestCase
    created_at      TEXT DEFAULT (datetime('now'))
);

-- 测试文件
CREATE TABLE test_files (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    constraint_id   INTEGER NOT NULL REFERENCES constraints(id),
    file_name       TEXT NOT NULL,
    content         TEXT NOT NULL,               -- 生成的 Python 代码
    coverage_report TEXT,                        -- JSON: 约束覆盖率
    validation_pass INTEGER DEFAULT 0,           -- 0:未验证 1:通过
    created_at      TEXT DEFAULT (datetime('now'))
);

-- 流程状态
CREATE TABLE pipeline_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    operator_id     INTEGER NOT NULL REFERENCES operators(id),
    status          TEXT NOT NULL DEFAULT 'running',  -- running/paused/completed/failed
    current_step    TEXT,
    state_snapshot  TEXT,                        -- JSON: AgentState 快照
    error_message   TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);
```

---

## 6. MCP Server 设计

### 6.1 数据库 MCP Tools

**核心原则：所有数据库操作都通过 MCP Tool 暴露，项目通过 `@Tool` 调用。**

| Tool 名称 | 参数 | 返回 | 说明 |
|-----------|------|------|------|
| **文档管理** | | | |
| `db_create_operator` | `name, source_url` | `operator_id` | 注册新算子 |
| `db_get_operator` | `name` | `Operator` | 查询算子信息 |
| `db_list_operators` | `offset, limit` | `list[Operator]` | 分页列出算子 |
| `db_save_document_version` | `operator_name, content` | `version, is_new` | 保存文档版本（自动计算 hash、检测变更） |
| `db_get_document_version` | `operator_name, version?` | `DocumentVersion` | 获取文档内容（默认最新版） |
| `db_diff_document_versions` | `operator_name, from_ver, to_ver` | `DocumentDiff` | 对比两个版本的差异 |
| **约束管理** | | | |
| `db_save_constraints` | `operator_name, constraint_data, doc_version` | `constraint_id` | 保存约束模型 |
| `db_get_constraints` | `operator_name, status?` | `OperatorConstraint` | 获取约束（可按状态过滤） |
| `db_update_constraint_status` | `constraint_id, status, comments?` | `None` | 更新约束审核状态 |
| `db_save_expressions` | `constraint_id, expressions` | `None` | 保存约束表达式 |
| **测试管理** | | | |
| `db_save_test_cases` | `constraint_id, test_cases` | `None` | 保存测试用例 |
| `db_get_test_cases` | `operator_name` | `list[TestCase]` | 获取测试用例 |
| `db_save_test_file` | `constraint_id, file_name, content, coverage` | `test_file_id` | 保存测试文件 |
| `db_get_test_file` | `operator_name` | `TestFile` | 获取测试文件 |
| **流程管理** | | | |
| `db_create_pipeline_run` | `operator_name` | `run_id` | 创建流程实例 |
| `db_update_pipeline_status` | `run_id, status, step, snapshot?` | `None` | 更新流程状态 |
| `db_get_pipeline_run` | `run_id` | `PipelineRun` | 查询流程状态 |

### 6.2 MCP Resources

| URI 模式 | 说明 |
|----------|------|
| `operator://list` | 列出所有已注册的算子 |
| `operator://{name}` | 获取指定算子的最新约束模型 |
| `operator://{name}/versions` | 获取指定算子的文档版本列表 |
| `operator://{name}/version/{ver}` | 获取指定版本的文档内容 |
| `operator://{name}/tests` | 获取指定算子的测试用例 |
| `template://test/python` | Python 测试文件模板 |

### 6.3 MCP Prompts

| 名称 | 说明 |
|------|------|
| `extract_constraints_prompt` | 约束提取的系统提示词模板 |
| `validate_constraints_prompt` | 约束自校验的提示词模板 |
| `generate_tests_prompt` | 测试生成的系统提示词模板 |

---

## 7. 多模型路由设计

```python
class LLMProvider(str, Enum):
    OPENAI = "openai"       # GPT-4o, GPT-4.1
    CLAUDE = "claude"       # Claude Opus/Sonnet/Haiku
    QWEN = "qwen"           # 通义千问
    WENXIN = "wenxin"       # 文心一言

class TaskComplexity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

ROUTING_TABLE = {
    TaskComplexity.HIGH:   ["claude:opus", "openai:gpt-4.1", "qwen:qwen-max"],
    TaskComplexity.MEDIUM: ["claude:sonnet", "openai:gpt-4o", "qwen:qwen-plus"],
    TaskComplexity.LOW:    ["claude:haiku", "openai:gpt-4o-mini", "qwen:qwen-turbo"],
}
```

节点与模型复杂度映射：

| 节点 | 复杂度 | 原因 |
|------|--------|------|
| doc_parser | LOW | 结构化拆分，规则为主 |
| constraint_extractor | HIGH | 深层语义理解和推理 |
| constraint_validator | HIGH | 逻辑推理校验一致性 |
| expr_generator | MEDIUM | 结构化转换 |
| test_planner | MEDIUM | 组合策略规划 |
| test_generator | MEDIUM | 数据填充 |
| codegen | LOW | 模板渲染 |

---

## 8. 并发处理设计

**单算子串行、多算子并发：**

```python
# 每个算子启动一个独立的 LangGraph 图实例
async def process_operator(operator_name: str, document_path: str) -> str:
    graph = compile_operator_graph()
    config = {"configurable": {"thread_id": f"operator_{operator_name}"}}
    result = await graph.ainvoke(
        {"operator_name": operator_name, "document_path": document_path},
        config=config
    )
    return result

# 多算子并发处理
async def process_batch(operator_docs: list[tuple[str, str]]) -> list[str]:
    tasks = [
        process_operator(name, path)
        for name, path in operator_docs
    ]
    return await asyncio.gather(*tasks)
```

每个算子的流程通过 `thread_id` 隔离，互不干扰。

---

## 9. 目录结构

```
src/
├── agent/                          # LangGraph 智能体
│   ├── __init__.py
│   ├── graph.py                    # 主图定义（compile）
│   ├── state.py                    # AgentState TypedDict
│   ├── nodes/                      # 图节点
│   │   ├── __init__.py
│   │   ├── doc_loader.py           # 文档加载（调用 MCP Tool）
│   │   ├── doc_parser.py           # 文档结构化拆分
│   │   ├── version_differ.py       # 文档版本 diff
│   │   ├── constraint_extractor.py # 约束提取（LLM）
│   │   ├── constraint_validator.py # 约束自校验（LLM）
│   │   ├── human_review.py         # 人工审核（interrupt）
│   │   ├── expr_generator.py       # 约束 → Python 表达式
│   │   ├── test_planner.py         # 测试规划
│   │   ├── test_generator.py       # 测试数据生成
│   │   ├── codegen.py              # Python 测试文件生成
│   │   ├── final_validator.py      # 最终校验
│   │   └── result_persister.py     # 结果持久化（调用 MCP Tool）
│   └── tools/                      # LangGraph @Tool（代理到 MCP）
│       ├── __init__.py
│       └── db_tools.py             # 数据库操作工具
│
├── mcp_server/                     # MCP Server（DB 独占层）
│   ├── __init__.py
│   ├── server.py                   # FastMCP 实例 + 注册
│   ├── db.py                       # SQLite 连接管理
│   ├── tools/                      # MCP Tools
│   │   ├── __init__.py
│   │   ├── operator_tools.py       # 算子 CRUD
│   │   ├── document_tools.py       # 文档版本管理
│   │   ├── constraint_tools.py     # 约束 CRUD + 审核
│   │   ├── test_tools.py           # 测试用例/文件 CRUD
│   │   └── pipeline_tools.py       # 流程状态管理
│   ├── resources/                  # MCP Resources
│   │   ├── __init__.py
│   │   └── operator_resources.py
│   └── prompts/                    # MCP Prompts
│       ├── __init__.py
│       └── templates.py
│
├── api/                            # FastAPI 应用
│   ├── __init__.py
│   ├── app.py                      # create_app()
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── operator.py             # /api/v1/operator/*
│   │   ├── constraint.py           # /api/v1/constraint/*
│   │   ├── test_case.py            # /api/v1/test/*
│   │   ├── review.py               # /api/v1/review/* (人工审核)
│   │   └── pipeline.py             # /api/v1/pipeline/*
│   ├── schemas/                    # 请求/响应 Pydantic 模型
│   │   ├── __init__.py
│   │   ├── operator.py
│   │   ├── constraint.py
│   │   ├── test_case.py
│   │   └── pipeline.py
│   └── dependencies.py             # FastAPI Depends
│
├── services/                       # 业务逻辑（共享层）
│   ├── __init__.py
│   ├── document_service.py         # 文档加载/解析
│   ├── constraint_service.py       # 约束提取/校验
│   ├── expression_service.py       # 约束 → 表达式
│   ├── test_case_service.py        # 测试用例生成
│   ├── version_service.py          # 文档版本管理
│   ├── llm_router.py               # 多模型路由
│   └── prompt_manager.py           # Prompt 模板管理
│
├── models/                         # 数据模型（Pydantic）
│   ├── __init__.py
│   ├── constraint.py               # 约束相关模型
│   ├── operator.py                 # 算子文档模型
│   ├── test_case.py                # 测试用例模型
│   ├── database.py                 # 数据库行模型
│   └── llm.py                      # LLM 配置模型
│
├── core/                           # 基础设施
│   ├── __init__.py
│   ├── config.py                   # Settings (pydantic-settings)
│   ├── exceptions.py               # 自定义异常
│   ├── logging.py                  # 日志配置
│   └── middleware.py               # FastAPI 中间件
│
├── templates/                      # Jinja2 模板
│   ├── test_case_python.j2         # Python 测试文件模板
│   └── constraint_py.j2            # Python 约束表达式模板
│
└── tests/                          # 测试
    ├── conftest.py
    ├── unit/
    │   ├── test_doc_parser.py
    │   ├── test_version_differ.py
    │   ├── test_constraint_extractor.py
    │   ├── test_expr_generator.py
    │   ├── test_codegen.py
    │   └── test_human_review.py
    ├── integration/
    │   ├── test_agent_graph.py
    │   ├── test_mcp_server.py
    │   ├── test_api_routes.py
    │   └── test_pipeline_flow.py
    └── fixtures/
        ├── sample_operator.md
        ├── sample_operator_v2.md
        └── expected_constraints.json
```

---

## 10. API 设计

### 10.1 核心端点

**算子管理**

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/v1/operators` | 列出所有算子 |
| POST | `/api/v1/operators` | 注册新算子 |
| GET | `/api/v1/operators/{name}` | 获取算子详情 |
| POST | `/api/v1/operators/{name}/document` | 上传算子文档（自动版本管理） |
| GET | `/api/v1/operators/{name}/versions` | 获取文档版本列表 |
| GET | `/api/v1/operators/{name}/versions/{ver}/diff` | 获取版本间差异 |

**约束管理**

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/v1/operators/{name}/constraints` | 获取约束模型 |
| POST | `/api/v1/operators/{name}/extract` | 触发约束提取 |
| GET | `/api/v1/operators/{name}/expressions` | 获取 Python 约束表达式 |

**人工审核**

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/v1/review/pending` | 获取待审核列表 |
| GET | `/api/v1/review/{name}` | 获取审核详情 |
| POST | `/api/v1/review/{name}/approve` | 通过审核 |
| POST | `/api/v1/review/{name}/reject` | 打回（附审核意见） |

**测试生成**

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/v1/operators/{name}/test-cases` | 生成测试用例 |
| GET | `/api/v1/operators/{name}/test-file` | 获取测试文件 |
| POST | `/api/v1/operators/{name}/test-file` | 生成测试文件 |

**流水线**

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/v1/pipeline/run` | 启动完整流程（支持单个/批量） |
| GET | `/api/v1/pipeline/{run_id}/status` | 查询流程状态 |
| POST | `/api/v1/pipeline/{run_id}/cancel` | 取消流程 |
| GET | `/api/v1/pipeline/list` | 列出所有流程实例 |

### 10.2 响应格式

```python
class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: str | None = None
    metadata: dict[str, Any] = {}
```

---

## 11. 关键技术决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| Agent 框架 | LangGraph | 支持状态图、条件边、`interrupt` 人工介入 |
| MCP 实现 | FastMCP (mcp Python SDK) | 轻量、独占 DB 层、与 LangGraph 互补 |
| 数据库 | SQLite | 轻量、零配置、单文件、适合当前规模 |
| DB 访问方式 | **仅通过 MCP Tool** | 项目不直接连 DB，MCP 是唯一入口 |
| API 框架 | FastAPI | 异步支持、Pydantic 原生集成、自动文档 |
| 数据校验 | Pydantic v2 | 严格模式、JSON Schema 生成、性能优异 |
| 测试文件 | Python (Jinja2 模板) | 全栈 Python，模板可热更新 |
| LLM 调用 | LangChain ChatModel | 统一接口支持多 Provider 切换 |
| 包管理 | uv | 快速依赖解析 |
| 配置管理 | pydantic-settings | 环境变量 + .env + 类型安全 |
| 人工审核 | LangGraph `interrupt` | 原生支持图暂停/恢复 |
| 并发模型 | asyncio.gather | 多算子并发、单算子串行 |

---

## 12. 风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 算子文档结构差异 | 解析失败率高 | doc_parser 多策略兼容 + LLM fallback |
| LLM 提取约束不完整 | 测试覆盖不足 | 自纠错循环 + 人工审核兜底 |
| 跨参数关系复杂 | 表达式生成困难 | 分层提取：先单参数，再跨参数 |
| 测试数据组合爆炸 | 生成文件过大 | test_planner 组合策略剪枝 |
| SQLite 并发写入 | 多算子并发时锁竞争 | WAL 模式 + 写入队列串行化 |
| 文档版本 diff 粒度 | 增量提取不准确 | 按段落级 diff + 语义分析 |
