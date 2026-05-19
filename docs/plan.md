# Operator Agent 实施计划

> 版本: v1.0 | 日期: 2026-05-15

## 项目现状

**已完成 (~30%)**:

- 共享模型 (enums, operator, constraint, test_case) — 全部 Pydantic 模型就绪
- MCP Server 文档解析管线 (section_splitter, document_parser) — 功能完整
- MCP Server 5 个工具 + 2 个资源 + SQLite DB — 可运行
- Agent 上传 API (FastAPI + MCP client + `/api/v1/upload`) — 可运行
- 21 个解析器测试 + 2 个 fixture 文档

**缺失 (~70%)**:

- LangGraph 智能体管线 (12 个节点, 目录为空)
- LLM 集成 (无 client, 无 prompt, 无路由)
- 约束提取 / 测试生成 (核心业务逻辑)
- 数据库 schema 扩展 (设计 6 张表, 目前只有 2 张)
- MCP Tools 扩展 (设计 20+ 个, 目前只有 5 个文档工具)
- REST API 扩展 (设计 15+ 端点, 目前只有 upload)
- 人工审核机制
- Agent / Shared 测试

---

## Phase 1: 基础设施完善 (数据库 + MCP Tools + 配置)

> 目标: 扩展数据库 schema 和 MCP 工具，为上层业务铺路

| # | 任务 | 文件 |
|---|------|------|
| 1.1 | 扩展 SQLite schema，增加 `constraints`, `constraint_expressions`, `test_cases`, `test_files`, `pipeline_runs` 5 张表 | `mcp_server/db.py` |
| 1.2 | 实现约束 CRUD 工具: `save_constraints`, `get_constraints`, `update_constraint_status` | `mcp_server/tools/constraint_tools.py` (新建) |
| 1.3 | 实现测试 CRUD 工具: `save_test_cases`, `get_test_cases`, `save_test_file`, `get_test_file` | `mcp_server/tools/test_tools.py` (新建) |
| 1.4 | 实现管线状态工具: `create_pipeline_run`, `update_pipeline_status`, `get_pipeline_run` | `mcp_server/tools/pipeline_tools.py` (新建) |
| 1.5 | 实现版本 diff 工具: `diff_document_versions` | `mcp_server/tools/document_tools.py` (扩展) |
| 1.6 | 注册所有新工具到 FastMCP server | `mcp_server/server.py` (扩展) |
| 1.7 | 扩展 MCP Resources: `operator://{name}/versions`, `operator://{name}/tests` | `mcp_server/server.py` (扩展) |
| 1.8 | 实现 MCP Prompts: `extract_constraints_prompt`, `validate_constraints_prompt`, `generate_tests_prompt` | `mcp_server/prompts/templates.py` (新建) |
| 1.9 | 扩展 `Settings` 配置: LLM provider, API keys, model routing | `agent/core/config.py` (扩展) |
| 1.10 | 补充子包 pyproject.toml 依赖 (langchain, langgraph, jinja2 等) | 各 `pyproject.toml` |
| 1.11 | 测试: 新 DB schema 迁移 + 新 MCP 工具单元测试 | `tests/mcp_server/` |

**预计**: ~15 个文件, 2-3 天

---

## Phase 2: LangGraph Agent 状态 + 图骨架 + LLM 集成

> 目标: 搭建 LangGraph 图骨架，实现 LLM 调用层

| # | 任务 | 文件 |
|---|------|------|
| 2.1 | 定义 `AgentState` TypedDict | `agent/state.py` (新建) |
| 2.2 | 实现 LLM Router: 多 provider 路由 (OpenAI/Claude/Qwen) | `agent/core/llm_router.py` (新建) |
| 2.3 | 实现 Prompt Manager: Jinja2 模板加载 + 变量注入 | `agent/core/prompt_manager.py` (新建) |
| 2.4 | 创建 Prompt 模板文件 | `agent/templates/extract_constraints.j2`, `validate_constraints.j2`, `generate_tests.j2` (新建) |
| 2.5 | 实现 LangGraph 工具代理层: Agent 调 MCP Tool 的 bridge | `agent/tools/db_tools.py` (新建) |
| 2.6 | 扩展 MCP Client: 支持所有新工具调用 | `agent/mcp_client.py` (扩展) |
| 2.7 | 测试: LLM router, prompt manager, state 序列化 | `tests/agent/` |

**预计**: ~10 个文件, 1-2 天

---

## Phase 3: LangGraph 节点实现 (核心业务逻辑)

> 目标: 实现 12 个 LangGraph 节点

| # | 节点 | LLM 复杂度 | 说明 | 文件 |
|---|------|-----------|------|------|
| 3.1 | `doc_loader` | -- | 读取 Markdown + MCP 查询/创建版本 | `agent/nodes/doc_loader.py` (新建) |
| 3.2 | `doc_parser` | LOW | 调 MCP parse_doc, 结构化分节 | `agent/nodes/doc_parser.py` (新建) |
| 3.3 | `version_differ` | -- | 新版本 diff 变更段落, 首版全量标记 | `agent/nodes/version_differ.py` (新建) |
| 3.4 | `constraint_extractor` | HIGH | LLM 语义提取 dtype/shape/format/跨参数/产品约束 | `agent/nodes/constraint_extractor.py` (新建) |
| 3.5 | `constraint_validator` | HIGH | LLM 自纠错, 检查一致性/遗漏/矛盾, 最多 3 轮 | `agent/nodes/constraint_validator.py` (新建) |
| 3.6 | `human_review` | -- | interrupt 暂停, 等待人工审核 | `agent/nodes/human_review.py` (新建) |
| 3.7 | `expr_generator` | MEDIUM | 约束 → Python 可执行表达式 | `agent/nodes/expr_generator.py` (新建) |
| 3.8 | `test_planner` | MEDIUM | 规划正向/反向/边界用例组合策略 | `agent/nodes/test_planner.py` (新建) |
| 3.9 | `test_generator` | MEDIUM | 生成具体测试数据 (TensorSpec) | `agent/nodes/test_generator.py` (新建) |
| 3.10 | `codegen` | LOW | Jinja2 模板生成 Python 测试文件 | `agent/nodes/codegen.py` (新建) |
| 3.11 | `final_validator` | -- | Python 语法检查 + 约束覆盖率校验 | `agent/nodes/final_validator.py` (新建) |
| 3.12 | `result_persister` | -- | MCP Tool 写入最终结果到 DB | `agent/nodes/result_persister.py` (新建) |

**预计**: 12 个节点文件, 3-4 天 (核心工作)

---

## Phase 4: 图组装 + API 路由

> 目标: 编排 LangGraph 图, 暴露 REST API

| # | 任务 | 文件 |
|---|------|------|
| 4.1 | 编译主图: 定义节点 + 边 + 条件路由 (自纠错循环, 审核分支) | `agent/graph.py` (新建) |
| 4.2 | Operator API: CRUD + 文档上传 | `agent/routes/operator.py` (新建) |
| 4.3 | Constraint API: 获取/触发提取/获取表达式 | `agent/routes/constraint.py` (新建) |
| 4.4 | Review API: pending 列表/approve/reject | `agent/routes/review.py` (新建) |
| 4.5 | Test API: 生成测试/获取测试文件 | `agent/routes/test_case.py` (新建) |
| 4.6 | Pipeline API: run/status/cancel/list | `agent/routes/pipeline.py` (新建) |
| 4.7 | 请求/响应 schema 定义 | `agent/schemas/` (新建 4 个文件) |
| 4.8 | FastAPI `create_app()` 注册所有路由 | `agent/main.py` (扩展) |
| 4.9 | Agent `__main__.py` 入口 | `agent/__main__.py` (新建) |

**预计**: ~15 个文件, 2 天

---

## Phase 5: 测试 + 集成验证

> 目标: 80%+ 测试覆盖率, E2E 验证

| # | 任务 | 文件 |
|---|------|------|
| 5.1 | Shared 模型测试 (约束/test_case 序列化 + 验证) | `tests/shared/test_models.py` (新建) |
| 5.2 | MCP Server 新工具单元测试 | `tests/mcp_server/test_constraint_tools.py`, `test_test_tools.py`, `test_pipeline_tools.py` (新建) |
| 5.3 | LangGraph 节点单元测试 (mock LLM + MCP) | `tests/agent/test_nodes.py` (新建) |
| 5.4 | LangGraph 图集成测试 | `tests/agent/test_graph.py` (新建) |
| 5.5 | API 路由集成测试 (httpx AsyncClient) | `tests/agent/test_api_routes.py` (新建) |
| 5.6 | E2E 测试: 完整流程 (上传 → 提取 → 审核 → 生成) | `tests/e2e/test_pipeline.py` (新建) |
| 5.7 | 覆盖率报告 + 修补到 80% | -- |

**预计**: ~8 个文件, 2 天

---

## Phase 6: 收尾 + 文档

> 目标: 代码质量 + 验证

| # | 任务 |
|---|------|
| 6.1 | ruff lint + mypy type check 全量通过 |
| 6.2 | `.env.example` 更新 (补充 LLM API keys 等) |
| 6.3 | 更新 `CLAUDE.md` 工具指令 (新增的 run 命令等) |
| 6.4 | 用 2-3 个真实算子文档验证 E2E 流程 |

**预计**: 1 天

---

## 总体预估

| 阶段 | 工作量 | 文件数 |
|------|--------|--------|
| Phase 1: 基础设施 | 2-3 天 | ~15 |
| Phase 2: Agent 骨架 + LLM | 1-2 天 | ~10 |
| Phase 3: 12 个节点 | 3-4 天 | 12 |
| Phase 4: 图 + API | 2 天 | ~15 |
| Phase 5: 测试 | 2 天 | ~8 |
| Phase 6: 收尾 | 1 天 | -- |
| **总计** | **~12 天** | **~60 文件** |

---

## 依赖关系

```
Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4 ──→ Phase 5 ──→ Phase 6
(DB/MCP)   (骨架/LLM)  (节点实现)   (图/API)     (测试)      (收尾)
```

阶段间严格串行，但同一阶段内的任务可并行执行。

---

## 关键风险

| 风险 | 缓解措施 |
|------|---------|
| LLM 提取约束不完整 | 自纠错循环 (最多 3 轮) + 人工审核兜底 |
| 算子文档结构差异大 | doc_parser 多策略兼容 + LLM fallback |
| 测试数据组合爆炸 | test_planner 组合策略剪枝 |
| SQLite 并发写入锁竞争 | WAL 模式 + 写入队列串行化 |
