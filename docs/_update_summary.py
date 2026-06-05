"""Update project_summary.html to reflect current pipeline state."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('docs/project_summary.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update overview date
html = html.replace(
    '更新日期: 2026-06-05',
    '更新日期: 2026-06-05 (Pipeline 重构: llm_description_extract 替代 3 节点)'
)

# 2. Update completion status
html = html.replace(
    '约 85%，文档解析、数据库层、Pipeline 全部 20 个节点（含 src_content 提取、function_signature 提取、function_explanation 提取、shape/dtype/dformat/optional/param_attr 提取、array_length 提取、allowed_range 提取、return_code 提取、determinism 提取、dtype_combo 提取、参数关系提取子图、build_param_relations 参数关系表达式构建节点、build_param_constraint 参数约束构建节点、assemble_result 汇编节点 + json_constraints 写入）可运行。',
    '约 87%，文档解析、数据库层、Pipeline 全部 18 个节点（含 llm_description_extract 一体化提取、function_signature 提取、function_explanation 提取、shape/dtype/dformat/optional/array_length 提取、allowed_range 提取、return_code 提取、determinism 提取、dtype_combo 提取、参数关系提取子图、build_param_relations 参数关系表达式构建节点、build_param_constraint 参数约束构建节点、assemble_result 汇编节点 + json_constraints 写入）可运行。'
)

# 3. Update directory structure — nodes section
old_nodes = """│           │   ├── state.py         # PipelineState TypedDict（带 merge_errors reducer）
│           │   ├── init_doc.py      # 节点1：版本检查 -> 保存 -> 解析
│           │   ├── product_support.py   # 节点2a（并行）：LLM 提取产品支持表
│           │   ├── parse_params.py      # 节点2b（并行）：LLM 提取函数参数
│           │   ├── function_signature_extract.py # 节点2c（并行）：LLM 提取函数签名
│           │   ├── function_explanation_extract.py # 节点2d（并行）：LLM 提取功能说明摘要 → document_versions.function_explanation_summary
│           │   ├── src_content_extract.py # 节点3：双Section路由 + LLM并发提取参数原文
│           │   ├── param_desc_extract.py # 节点4：从src_content生成结构化参数描述表格
│           │   ├── shape_extract.py     # 节点5a（并行）：逐参数LLM提取无条件shape
│           │   ├── dtype_extract.py     # 节点5b（并行）：逐参数LLM提取数据类型
│           │   ├── dformat_extract.py   # 节点5c（并行）：逐参数LLM提取数据格式
│           │   ├── optional_extract.py  # 节点5d（并行）：逐参数LLM判断可选性
│           │   ├── param_attr_extract.py # 节点5f（并行）：正则提取非连续Tensor支持 + param_desc
│           │   ├── array_length_extract.py # 节点5g（并行）：LLM提取数组长度
│           │   ├── allowed_range_extract.py # 节点5h（并行）：LLM提取参数取值范围约束
│           │   ├── return_code_extract.py # 节点5i（并行）：LLM提取返回码/错误码
│           │   ├── determinism_extract.py # 节点5j（并行）：LLM提取确定性计算信息
│           │   ├── dtype_combo_extract.py # 节点5k（并行）：LLM提取数据类型组合
│           │   ├── build_param_relations.py # 节点5.5r（顺序）：LLM 提取参数关系表达式 + 按平台分组
│           │   ├── build_param_constraint.py # 节点5.5（顺序）：LLM 构建参数约束JSON（shape→dimensions + allowed_range_value）
│           │   ├── assemble_result.py # 节点6（顺序）：汇编所有提取结果→constraints_result表
│           │   └── param_relation_extract/  # 节点5e（并行）：参数耦合关系提取子图"""

new_nodes = """│           │   ├── state.py         # PipelineState TypedDict（带 merge_errors reducer）
│           │   ├── init_doc.py      # 节点1：版本检查 -> 保存 -> 解析
│           │   ├── product_support.py   # 节点2a（并行）：LLM 提取产品支持表
│           │   ├── parse_params.py      # 节点2b（并行）：LLM 提取函数参数
│           │   ├── function_signature_extract.py # 节点2c（并行）：LLM 提取函数签名
│           │   ├── function_explanation_extract.py # 节点2d（并行）：LLM 提取功能说明摘要
│           │   ├── llm_description_extract.py # 节点3：一体化LLM提取（替代原src_content+param_desc+param_attr三节点）
│           │   ├── shape_extract.py     # 节点4a（并行）：逐参数LLM提取无条件shape
│           │   ├── dtype_extract.py     # 节点4b（并行）：逐参数LLM提取数据类型
│           │   ├── dformat_extract.py   # 节点4c（并行）：逐参数LLM提取数据格式
│           │   ├── optional_extract.py  # 节点4d（并行）：逐参数LLM判断可选性
│           │   ├── array_length_extract.py # 节点4g（并行）：LLM提取数组长度
│           │   ├── allowed_range_extract.py # 节点4h（并行）：LLM提取参数取值范围约束
│           │   ├── return_code_extract.py # 节点4i（并行）：LLM提取返回码/错误码
│           │   ├── determinism_extract.py # 节点4j（并行）：LLM提取确定性计算信息
│           │   ├── dtype_combo_extract.py # 节点4k（并行）：LLM提取数据类型组合
│           │   ├── build_param_relations.py # 节点5.5r（顺序）：LLM 提取参数关系表达式 + 按平台分组
│           │   ├── build_param_constraint.py # 节点5.5（顺序）：LLM 构建参数约束JSON（shape→dimensions + allowed_range_value）
│           │   ├── assemble_result.py # 节点6（顺序）：汇编所有提取结果→constraints_result表
│           │   └── param_relation_extract/  # 节点4e（并行）：参数耦合关系提取子图"""

html = html.replace(old_nodes, new_nodes)

# 4. Update sidebar nav
html = html.replace(
    '<li><a class="nav-item" data-target="sec-node3"><span class="arrow empty">&rsaquo;</span>节点3: src_content</a></li>\n'
    '            <li><a class="nav-item" data-target="sec-node4"><span class="arrow empty">&rsaquo;</span>节点4: param_desc</a></li>\n'
    '            <li><a class="nav-item" data-target="sec-node5a"><span class="arrow empty">&rsaquo;</span>节点5a: shape</a></li>\n'
    '            <li><a class="nav-item" data-target="sec-node5b"><span class="arrow empty">&rsaquo;</span>节点5b: dtype</a></li>\n'
    '            <li><a class="nav-item" data-target="sec-node5c"><span class="arrow empty">&rsaquo;</span>节点5c: dformat</a></li>\n'
    '            <li><a class="nav-item" data-target="sec-node5d"><span class="arrow empty">&rsaquo;</span>节点5d: optional</a></li>\n'
    '            <li><a class="nav-item" data-target="sec-node5e"><span class="arrow empty">&rsaquo;</span>节点5e: param_relation</a></li>\n'
    '            <li><a class="nav-item" data-target="sec-node5f"><span class="arrow empty">&rsaquo;</span>节点5f: param_attr</a></li>\n'
    '            <li><a class="nav-item" data-target="sec-node5g"><span class="arrow empty">&rsaquo;</span>节点5g: array_length</a></li>\n'
    '            <li><a class="nav-item" data-target="sec-node5h"><span class="arrow empty">&rsaquo;</span>节点5h: allowed_range</a></li>\n'
    '            <li><a class="nav-item" data-target="sec-node5i"><span class="arrow empty">&rsaquo;</span>节点5i: return_codes</a></li>\n'
    '            <li><a class="nav-item" data-target="sec-node5j"><span class="arrow empty">&rsaquo;</span>节点5j: determinism</a></li>\n'
    '            <li><a class="nav-item" data-target="sec-node5k"><span class="arrow empty">&rsaquo;</span>节点5k: dtype_combo</a></li>',
    '<li><a class="nav-item" data-target="sec-node3"><span class="arrow empty">&rsaquo;</span>节点3: llm_description</a></li>\n'
    '            <li><a class="nav-item" data-target="sec-node5a"><span class="arrow empty">&rsaquo;</span>节点4a: shape</a></li>\n'
    '            <li><a class="nav-item" data-target="sec-node5b"><span class="arrow empty">&rsaquo;</span>节点4b: dtype</a></li>\n'
    '            <li><a class="nav-item" data-target="sec-node5c"><span class="arrow empty">&rsaquo;</span>节点4c: dformat</a></li>\n'
    '            <li><a class="nav-item" data-target="sec-node5d"><span class="arrow empty">&rsaquo;</span>节点4d: optional</a></li>\n'
    '            <li><a class="nav-item" data-target="sec-node5e"><span class="arrow empty">&rsaquo;</span>节点4e: param_relation</a></li>\n'
    '            <li><a class="nav-item" data-target="sec-node5g"><span class="arrow empty">&rsaquo;</span>节点4g: array_length</a></li>\n'
    '            <li><a class="nav-item" data-target="sec-node5h"><span class="arrow empty">&rsaquo;</span>节点4h: allowed_range</a></li>\n'
    '            <li><a class="nav-item" data-target="sec-node5i"><span class="arrow empty">&rsaquo;</span>节点4i: return_codes</a></li>\n'
    '            <li><a class="nav-item" data-target="sec-node5j"><span class="arrow empty">&rsaquo;</span>节点4j: determinism</a></li>\n'
    '            <li><a class="nav-item" data-target="sec-node5k"><span class="arrow empty">&rsaquo;</span>节点4k: dtype_combo</a></li>'
)

# 5. Replace sec-node3 + sec-node4 sections with llm_description_extract
idx3 = html.find('<section class="content-section" id="sec-node3">')
idx5a = html.find('<section class="content-section" id="sec-node5a">')
if idx3 >= 0 and idx5a >= 0:
    new_sec3 = '''<section class="content-section" id="sec-node3">
<h1>节点3: llm_description_extract_node（顺序执行，等待 2a~2d 完成）</h1>
<div class="node-io">
<h3>数据流 &amp; 依赖关系</h3>
<div class="io-row"><span class="io-label">上游节点</span><span class="io-val"><span class="io-tag">product_support (2a)</span> <span class="io-tag">parse_params (2b)</span> <span class="io-tag">function_signature_extract (2c)</span> <span class="io-tag">function_explanation_extract (2d)</span> — 等待四者全部完成</span></div>
<div class="io-row"><span class="io-label">同级节点</span><span class="io-val">无（独占顺序执行）</span></div>
<div class="io-row"><span class="io-label">下游节点</span><span class="io-val"><span class="io-tag io-tag-down">shape (4a)</span> <span class="io-tag io-tag-down">dtype (4b)</span> <span class="io-tag io-tag-down">dformat (4c)</span> <span class="io-tag io-tag-down">optional (4d)</span> <span class="io-tag io-tag-down">param_relation (4e)</span> <span class="io-tag io-tag-down">array_length (4g)</span> <span class="io-tag io-tag-down">allowed_range (4h)</span> <span class="io-tag io-tag-down">return_codes (4i)</span> <span class="io-tag io-tag-down">determinism (4j)</span> <span class="io-tag io-tag-down">dtype_combo (4k)</span> — 10个节点并行扇出</span></div>
<div class="io-row"><span class="io-label">State 输入</span><span class="io-val"><code>doc_id</code>, <code>parameters</code>（来自节点2b，含 function_name/param_name/param_type）</span></div>
<div class="io-row"><span class="io-label">MCP 读取</span><span class="io-val"><code>get_section("params_get_workspace")</code>, <code>get_section("return_codes_get_workspace")</code>, <code>get_section("constraints")</code>, <code>get_section("params_execute")</code>, <code>get_section("return_codes_execute")</code></span></div>
<div class="io-row"><span class="io-label">State 输出</span><span class="io-val"><code>parameters</code>（追加 llm_description, src_content, direction, is_support_discontinuous）, <code>error</code></span></div>
<div class="io-row"><span class="io-label">DB 写入</span><span class="io-val"><code>parameters.llm_description</code>, <code>parameters.src_content</code>, <code>parameters.direction</code>, <code>parameters.is_support_discontinuous</code> (UPDATE)</span></div>
</div>

<p><strong>架构变更</strong>：本节点<strong>替代</strong>了原来的三个节点（<code>src_content_extract</code> + <code>param_desc_extract</code> + <code>param_attr_extract</code>），将三步 LLM 调用合并为<strong>一次 LLM 调用</strong>，同时提取四个字段。</p>
<p><strong>流程</strong>：</p>
<div class="flow-chart">llm_description_extract_node(state)
  │
  ├─ state.get("parameters", [])  ← 从 state 读取参数列表
  │
  ├─ 按 function_name 分类：
  │    ├─ GetWorkspaceSize 参数 → 获取 ws_sections_text
  │    │    └─ MCP: get_section × 3 (params_get_workspace, return_codes_get_workspace, constraints)
  │    └─ Execute 参数 → 获取 exe_sections_text
  │         └─ MCP: get_section × 3 (params_execute, return_codes_execute, constraints)
  │
  ├─ 逐参数并发 LLM（asyncio.Semaphore(5)）:
  │    └─ LLM_DESCRIPTION_EXTRACT_PROMPT.format(param_name, section_content)
  │       └─ 一次调用同时提取：
  │          ├─ llm_description: 逻辑完整的描述文本（平台无关通用属性）
  │          ├─ src_content: 原始文档文本（溯源依据）
  │          ├─ direction: 输入/输出
  │          └─ is_support_discontinuous: true/false/null
  │
  ├─ MCP: update_llm_descriptions(doc_id, updates)
  │    └─ 批量 UPDATE 四个字段
  │
  └─ return {"parameters": enriched_params, "error": None}  ← 合并到 state 传递给下游</div>
<p><strong>输出状态</strong>：<code>parameters: list[dict]</code>, <code>error</code></p>
<p><strong>与旧节点对比</strong>：</p>
<table>
<thead><tr><th>旧节点</th><th>旧字段</th><th>新节点</th><th>新字段</th></tr></thead>
<tbody>
<tr><td>src_content_extract</td><td>src_content</td><td rowspan="3">llm_description_extract<br>（一次 LLM 调用）</td><td>src_content</td></tr>
<tr><td>param_desc_extract</td><td>description + direction</td><td>llm_description + direction</td></tr>
<tr><td>param_attr_extract</td><td>is_support_discontinuous + param_desc</td><td>is_support_discontinuous（param_desc 改由 build_param_constraint 从 llm_description 正则提取）</td></tr>
</tbody>
</table>
<p><strong>LLM Prompt 设计要点</strong>：只包含<strong>平台无关的通用属性</strong>（所有平台都适用的约束），不包含平台特定约束（如 "Atlas A2 下..."）。平台特定信息由下游 allowed_range_extract、determinism_extract 等节点单独处理。</p>


</section>
'''
    html = html[:idx3] + new_sec3 + html[idx5a:]

# 6. Remove sec-node5f (param_attr) section
idx5f_start = html.find('<section class="content-section" id="sec-node5f">')
if idx5f_start >= 0:
    idx5f_end = html.find('</section>', idx5f_start) + len('</section>')
    html = html[:idx5f_start] + html[idx5f_end:]

# 7. Update all downstream node upstream references
# shape (5a → 4a)
html = html.replace(
    '节点5a: shape_extract_node（与 5b~5k、5e 并行执行）',
    '节点4a: shape_extract_node（与 4b~4k、4e 并行执行）'
)
html = html.replace(
    '<div class="io-row"><span class="io-label">上游节点</span><span class="io-val"><span class="io-tag">param_desc_extract (节点4)</span></span></div>\n<div class="io-row"><span class="io-label">同级节点</span><span class="io-val"><span class="io-tag io-tag-sib">5b~5k + param_relation (5e)</span> — 11个节点并行（当前为 5a shape）</span></div>',
    '<div class="io-row"><span class="io-label">上游节点</span><span class="io-val"><span class="io-tag">llm_description_extract (节点3)</span></span></div>\n<div class="io-row"><span class="io-label">同级节点</span><span class="io-val"><span class="io-tag io-tag-sib">4b~4k + param_relation (4e)</span> — 10个节点并行（当前为 4a shape）</span></div>'
)

# dtype (5b → 4b)
html = html.replace(
    '节点5b: dtype_extract_node（与 5a、5c~5k、5e 并行执行）',
    '节点4b: dtype_extract_node（与 4a、4c~4k、4e 并行执行）'
)
html = html.replace(
    '<div class="io-row"><span class="io-label">上游节点</span><span class="io-val"><span class="io-tag">param_desc_extract (节点4)</span></span></div>\n<div class="io-row"><span class="io-label">同级节点</span><span class="io-val"><span class="io-tag io-tag-sib">5a、5c~5k + param_relation (5e)</span> — 11个节点并行（当前为 5b dtype）</span></div>',
    '<div class="io-row"><span class="io-label">上游节点</span><span class="io-val"><span class="io-tag">llm_description_extract (节点3)</span></span></div>\n<div class="io-row"><span class="io-label">同级节点</span><span class="io-val"><span class="io-tag io-tag-sib">4a、4c~4k + param_relation (4e)</span> — 10个节点并行（当前为 4b dtype）</span></div>'
)

# dformat (5c → 4c)
html = html.replace(
    '节点5c: dformat_extract_node（与 5a、5b、5d~5k、5e 并行执行）',
    '节点4c: dformat_extract_node（与 4a、4b、4d~4k、4e 并行执行）'
)
html = html.replace(
    '<div class="io-row"><span class="io-label">上游节点</span><span class="io-val"><span class="io-tag">param_desc_extract (节点4)</span></span></div>\n<div class="io-row"><span class="io-label">同级节点</span><span class="io-val"><span class="io-tag io-tag-sib">5a、5b、5d~5k + param_relation (5e)</span> — 11个节点并行（当前为 5c dformat）</span></div>',
    '<div class="io-row"><span class="io-label">上游节点</span><span class="io-val"><span class="io-tag">llm_description_extract (节点3)</span></span></div>\n<div class="io-row"><span class="io-label">同级节点</span><span class="io-val"><span class="io-tag io-tag-sib">4a、4b、4d~4k + param_relation (4e)</span> — 10个节点并行（当前为 4c dformat）</span></div>'
)

# optional (5d → 4d)
html = html.replace(
    '节点5d: optional_extract_node（与 5a~5c、5f~5k、5e 并行执行）',
    '节点4d: optional_extract_node（与 4a~4c、4g~4k、4e 并行执行）'
)
html = html.replace(
    '<div class="io-row"><span class="io-label">上游节点</span><span class="io-val"><span class="io-tag">param_desc_extract (节点4)</span></span></div>\n<div class="io-row"><span class="io-label">同级节点</span><span class="io-val"><span class="io-tag io-tag-sib">5a~5c、5f~5k + param_relation (5e)</span> — 11个节点并行（当前为 5d optional）</span></div>',
    '<div class="io-row"><span class="io-label">上游节点</span><span class="io-val"><span class="io-tag">llm_description_extract (节点3)</span></span></div>\n<div class="io-row"><span class="io-label">同级节点</span><span class="io-val"><span class="io-tag io-tag-sib">4a~4c、4g~4k + param_relation (4e)</span> — 10个节点并行（当前为 4d optional）</span></div>'
)

# param_relation (5e → 4e)
html = html.replace(
    '节点5e: param_relation_extract（与 5a~5d、5f~5k 并行执行）',
    '节点4e: param_relation_extract（与 4a~4d、4g~4k 并行执行）'
)
html = html.replace(
    '<div class="io-row"><span class="io-label">上游节点</span><span class="io-val"><span class="io-tag">param_desc_extract (节点4)</span></span></div>\n<div class="io-row"><span class="io-label">同级节点</span><span class="io-val"><span class="io-tag io-tag-sib">5a~5d、5f~5k</span> — 11个节点并行（当前为 5e param_relation）</span></div>',
    '<div class="io-row"><span class="io-label">上游节点</span><span class="io-val"><span class="io-tag">llm_description_extract (节点3)</span></span></div>\n<div class="io-row"><span class="io-label">同级节点</span><span class="io-val"><span class="io-tag io-tag-sib">4a~4d、4g~4k</span> — 10个节点并行（当前为 4e param_relation）</span></div>'
)

# array_length (5g → 4g)
html = html.replace(
    '节点5g: array_length_extract_node（与 5a~5f、5h~5k、5e 并行执行）',
    '节点4g: array_length_extract_node（与 4a~4d、4h~4k、4e 并行执行）'
)
html = html.replace(
    '<div class="io-row"><span class="io-label">上游节点</span><span class="io-val"><span class="io-tag">param_desc_extract (节点4)</span></span></div>\n<div class="io-row"><span class="io-label">同级节点</span><span class="io-val"><span class="io-tag io-tag-sib">5a~5f、5h~5k + param_relation (5e)</span> — 11个节点并行（当前为 5g array_length）</span></div>',
    '<div class="io-row"><span class="io-label">上游节点</span><span class="io-val"><span class="io-tag">llm_description_extract (节点3)</span></span></div>\n<div class="io-row"><span class="io-label">同级节点</span><span class="io-val"><span class="io-tag io-tag-sib">4a~4d、4h~4k + param_relation (4e)</span> — 10个节点并行（当前为 4g array_length）</span></div>'
)

# allowed_range (5h → 4h)
html = html.replace(
    '节点5h: allowed_range_extract_node（与 5a~5g、5i~5k、5e 并行执行）',
    '节点4h: allowed_range_extract_node（与 4a~4g、4i~4k、4e 并行执行）'
)
html = html.replace(
    '<div class="io-row"><span class="io-label">上游节点</span><span class="io-val"><span class="io-tag">param_desc_extract (节点4)</span></span></div>\n<div class="io-row"><span class="io-label">同级节点</span><span class="io-val"><span class="io-tag io-tag-sib">5a~5g、5i~5k + param_relation (5e)</span> — 11个节点并行（当前为 5h allowed_range）</span></div>',
    '<div class="io-row"><span class="io-label">上游节点</span><span class="io-val"><span class="io-tag">llm_description_extract (节点3)</span></span></div>\n<div class="io-row"><span class="io-label">同级节点</span><span class="io-val"><span class="io-tag io-tag-sib">4a~4g、4i~4k + param_relation (4e)</span> — 10个节点并行（当前为 4h allowed_range）</span></div>'
)

# return_codes (5i → 4i)
html = html.replace(
    '节点5i: return_code_extract_node（与 5a~5h、5j、5k、5e 并行执行）',
    '节点4i: return_code_extract_node（与 4a~4h、4j、4k、4e 并行执行）'
)
html = html.replace(
    '<div class="io-row"><span class="io-label">上游节点</span><span class="io-val"><span class="io-tag">param_desc_extract (节点4)</span></span></div>\n<div class="io-row"><span class="io-label">同级节点</span><span class="io-val"><span class="io-tag io-tag-sib">5a~5h、5j、5k + param_relation (5e)</span> — 11个节点并行（当前为 5i return_codes）</span></div>',
    '<div class="io-row"><span class="io-label">上游节点</span><span class="io-val"><span class="io-tag">llm_description_extract (节点3)</span></span></div>\n<div class="io-row"><span class="io-label">同级节点</span><span class="io-val"><span class="io-tag io-tag-sib">4a~4h、4j、4k + param_relation (4e)</span> — 10个节点并行（当前为 4i return_codes）</span></div>'
)

# determinism (5j → 4j)
html = html.replace(
    '节点5j: determinism_extract_node（与 5a~5i、5k、5e 并行执行）',
    '节点4j: determinism_extract_node（与 4a~4i、4k、4e 并行执行）'
)
html = html.replace(
    '<div class="io-row"><span class="io-label">上游节点</span><span class="io-val"><span class="io-tag">param_desc_extract (节点4)</span></span></div>\n<div class="io-row"><span class="io-label">同级节点</span><span class="io-val"><span class="io-tag io-tag-sib">5a~5i、5k + param_relation (5e)</span> — 11个节点并行（当前为 5j determinism）</span></div>',
    '<div class="io-row"><span class="io-label">上游节点</span><span class="io-val"><span class="io-tag">llm_description_extract (节点3)</span></span></div>\n<div class="io-row"><span class="io-label">同级节点</span><span class="io-val"><span class="io-tag io-tag-sib">4a~4i、4k + param_relation (4e)</span> — 10个节点并行（当前为 4j determinism）</span></div>'
)

# dtype_combo (5k → 4k)
html = html.replace(
    '节点5k: dtype_combo_extract_node（与 5a~5j 并行执行）',
    '节点4k: dtype_combo_extract_node（与 4a~4j 并行执行）'
)
html = html.replace(
    '<div class="io-row"><span class="io-label">上游节点</span><span class="io-val"><span class="io-tag">param_desc_extract (节点4)</span></span></div>\n<div class="io-row"><span class="io-label">同级节点</span><span class="io-val"><span class="io-tag io-tag-sib">5a~5j + param_relation</span> — 12个节点并行（当前为 5k dtype_combo）</span></div>',
    '<div class="io-row"><span class="io-label">上游节点</span><span class="io-val"><span class="io-tag">llm_description_extract (节点3)</span></span></div>\n<div class="io-row"><span class="io-label">同级节点</span><span class="io-val"><span class="io-tag io-tag-sib">4a~4j + param_relation (4e)</span> — 10个节点并行（当前为 4k dtype_combo）</span></div>'
)

# build_param_constraint upstream
html = html.replace(
    '<div class="io-row"><span class="io-label">上游节点</span><span class="io-val"><span class="io-tag">5a~5k + param_relation</span> — 全部 12 个并行节点（LangGraph 扇入汇合）</span></div>',
    '<div class="io-row"><span class="io-label">上游节点</span><span class="io-val"><span class="io-tag">4a~4k + param_relation (4e)</span> — 全部 10 个并行节点 + build_param_relations（LangGraph 扇入汇合）</span></div>'
)

# 8. Update timing chart
html = html.replace(
    '    section 顺序\n    src_content_extract (LLM 并发提取原文) :3, 4\n    param_desc_extract (生成描述表格) :4, 5\n\n    section 并行 5a~5k\n    shape_extract (逐参数提取 shape) :5, 7\n    dtype_extract (逐参数提取 dtype) :5, 7\n    dformat_extract (逐参数提取数据格式) :5, 7\n    optional_extract (逐参数判断可选) :5, 7\n    param_attr_extract (正则提取非连续Tensor+param_desc) :5, 7\n    array_length_extract (LLM提取数组长度) :5, 7\n    allowed_range_extract (LLM提取取值范围约束) :5, 7\n    return_code_extract (LLM提取返回码/错误码) :5, 7\n    determinism_extract (LLM提取确定性计算信息) :5, 7\n    dtype_combo_extract (LLM提取数据类型组合) :5, 7\n    param_relation_extract (子图: 提取参数耦合关系) :5, 7',
    '    section 顺序\n    llm_description_extract (一体化LLM提取) :3, 4\n\n    section 并行 4a~4k\n    shape_extract (逐参数提取 shape) :4, 6\n    dtype_extract (逐参数提取 dtype) :4, 6\n    dformat_extract (逐参数提取数据格式) :4, 6\n    optional_extract (逐参数判断可选) :4, 6\n    array_length_extract (LLM提取数组长度) :4, 6\n    allowed_range_extract (LLM提取取值范围约束) :4, 6\n    return_code_extract (LLM提取返回码/错误码) :4, 6\n    determinism_extract (LLM提取确定性计算信息) :4, 6\n    dtype_combo_extract (LLM提取数据类型组合) :4, 6\n    param_relation_extract (子图: 提取参数耦合关系) :4, 6'
)

# 9. Update DB schema — parameters table
html = html.replace(
    '    direction TEXT DEFAULT \'input\',  -- \'input\' | \'output\' (param_desc_extract填充)\n    src_content TEXT,                -- 原始参数描述 Markdown (src_content_extract填充) (ALTER TABLE 迁移v3添加)\n    description TEXT,                -- Markdown 格式 (param_desc_extract填充)\n    dtype_desc TEXT,                 -- 数据类型 (dtype_extract填充)',
    '    direction TEXT DEFAULT \'input\',  -- \'input\' | \'output\' (llm_description_extract填充)\n    src_content TEXT,                -- 原始参数描述文本 (llm_description_extract填充) (ALTER TABLE 迁移v3添加)\n    dtype_desc TEXT,                 -- 数据类型 (dtype_extract填充)'
)
html = html.replace(
    "    param_constraint    TEXT NOT NULL DEFAULT '{}',  -- JSON: 按平台分组的参数约束 (build_param_constraint填充) (ALTER TABLE 迁移v19添加)\n    created_at TEXT,\n    UNIQUE(doc_id, function_name, param_name)\n)",
    "    param_constraint    TEXT NOT NULL DEFAULT '{}',  -- JSON: 按平台分组的参数约束 (build_param_constraint填充) (ALTER TABLE 迁移v19添加)\n    llm_description     TEXT NOT NULL DEFAULT '',  -- LLM 逻辑完整描述 (llm_description_extract填充) (ALTER TABLE 迁移v31添加, v32回填+删除description)\n    created_at TEXT,\n    UNIQUE(doc_id, function_name, param_name)\n)\n-- 注: description 列已在 v32 迁移中删除，数据回填到 llm_description"
)

# 10. Update various description references in node flow charts
html = html.replace('params_text=description)', 'params_text=llm_description)')
html = html.replace('过滤 description 非空的参数', '过滤 llm_description 非空的参数')

# 11. Update pipeline flowchart
html = html.replace(
    '    H --> J["src_content_extract (3)\\nLLM 并发提取参数原文\\nMCP: update_param_src_content"]\n    I --> J\n    I2 --> J\n    I3 --> J\n    J --> K["param_desc_extract (4)\\n从 src_content 生成描述表格\\nMCP: update_param_descriptions"]\n    K --> L["shape_extract (5a)\\nLLM 提取 shape"]\n    K --> M["dtype_extract (5b)\\nLLM 提取 dtype"]\n    K --> N["dformat_extract (5c)\\nLLM 提取数据格式"]\n    K --> P["optional_extract (5d)\\nLLM 判断 is_optional"]\n    K --> P2["param_attr_extract (5f)\\n正则提取非连续Tensor + param_desc"]\n    K --> P3["array_length_extract (5g)\\nLLM提取数组长度"]\n    K --> P4["allowed_range_extract (5h)\\nLLM提取参数取值范围约束"]\n    K --> P5["return_code_extract (5i)\\nLLM提取返回码/错误码"]\n    K --> P6["determinism_extract (5j)\\nLLM提取确定性计算信息\\n→ platform_support.deterministic_computing"]\n    K --> P7["dtype_combo_extract (5k)\\nLLM提取数据类型组合"]\n    K --> Q["param_relation_extract (5e)\\n子图：LLM 提取参数耦合关系"]\n    Q --> BPR["build_param_relations (5.5r)\\nLLM 提取参数关系表达式\\n按平台分组"]\n    L --> BPC["build_param_constraint (5.5)\\nLLM: shape→dimensions\\nLLM: allowed_range_value\\n组装 param_constraint JSON"]\n    M --> BPC\n    N --> BPC\n    P --> BPC\n    P2 --> BPC\n    P3 --> BPC\n    P4 --> BPC\n    P5 --> BPC\n    P6 --> BPC\n    P7 --> BPC\n    BPR --> BPC',
    '    H --> LDE["llm_description_extract (3)\\n一体化LLM提取：\\nllm_description + src_content\\n+ direction + is_support_discontinuous\\n替代原 src_content + param_desc + param_attr 三节点"]\n    I --> LDE\n    I2 --> LDE\n    I3 --> LDE\n    LDE --> L["shape_extract (4a)\\nLLM 提取 shape"]\n    LDE --> M["dtype_extract (4b)\\nLLM 提取 dtype"]\n    LDE --> N["dformat_extract (4c)\\nLLM 提取数据格式"]\n    LDE --> P["optional_extract (4d)\\nLLM 判断 is_optional"]\n    LDE --> P3["array_length_extract (4g)\\nLLM提取数组长度"]\n    LDE --> P4["allowed_range_extract (4h)\\nLLM提取参数取值范围约束"]\n    LDE --> P5["return_code_extract (4i)\\nLLM提取返回码/错误码"]\n    LDE --> P6["determinism_extract (4j)\\nLLM提取确定性计算信息"]\n    LDE --> P7["dtype_combo_extract (4k)\\nLLM提取数据类型组合"]\n    LDE --> Q["param_relation_extract (4e)\\n子图：LLM 提取参数耦合关系"]\n    Q --> BPR["build_param_relations (5.5r)\\nLLM 提取参数关系表达式\\n按平台分组"]\n    L --> BPC["build_param_constraint (5.5)\\nLLM: shape→dimensions\\nLLM: allowed_range_value\\n组装 param_constraint JSON"]\n    M --> BPC\n    N --> BPC\n    P --> BPC\n    P3 --> BPC\n    P4 --> BPC\n    P5 --> BPC\n    P6 --> BPC\n    P7 --> BPC\n    BPR --> BPC'
)

# 12. Update mermaid styles
html = html.replace(
    '    style J fill:#faf5ff,stroke:#805ad5\n    style K fill:#faf5ff,stroke:#805ad5\n    style L fill:#ebf8ff,stroke:#3182ce\n    style M fill:#ebf8ff,stroke:#3182ce\n    style N fill:#ebf8ff,stroke:#3182ce\n    style P fill:#ebf8ff,stroke:#3182ce\n    style P2 fill:#ebf8ff,stroke:#3182ce\n    style P3 fill:#ebf8ff,stroke:#3182ce\n    style P4 fill:#ebf8ff,stroke:#3182ce\n    style P5 fill:#ebf8ff,stroke:#3182ce\n    style P6 fill:#ebf8ff,stroke:#3182ce\n    style P7 fill:#ebf8ff,stroke:#3182ce\n    style Q fill:#ebf8ff,stroke:#3182ce',
    '    style LDE fill:#faf5ff,stroke:#805ad5\n    style L fill:#ebf8ff,stroke:#3182ce\n    style M fill:#ebf8ff,stroke:#3182ce\n    style N fill:#ebf8ff,stroke:#3182ce\n    style P fill:#ebf8ff,stroke:#3182ce\n    style P3 fill:#ebf8ff,stroke:#3182ce\n    style P4 fill:#ebf8ff,stroke:#3182ce\n    style P5 fill:#ebf8ff,stroke:#3182ce\n    style P6 fill:#ebf8ff,stroke:#3182ce\n    style P7 fill:#ebf8ff,stroke:#3182ce\n    style Q fill:#ebf8ff,stroke:#3182ce'
)

# 13. Update sec-issue-fe items
html = html.replace(
    '<li><strong>参数属性提取</strong>：<code>param_attr_extract</code> 节点（5f）从 description 表格中正则提取两个属性：<code>is_support_discontinuous</code>（非连续Tensor支持，匹配 √/✓/✔/支持）和 <code>param_desc</code>（描述摘要，从"描述"行提取）。结果分别存入 <code>is_support_discontinuous</code> 列（JSON TEXT）和 <code>param_desc</code> 列（TEXT）。前端参数表新增"描述摘要"列显示 <code>param_desc</code>。</li>',
    '<li><del>参数属性提取</del> &check; 已合并 — 原 <code>param_attr_extract</code> 节点（5f）已移除，<code>is_support_discontinuous</code> 提取合并到 <code>llm_description_extract</code> 节点（一次 LLM 调用同时提取四个字段）。<code>param_desc</code> 改由 <code>build_param_constraint</code> 从 <code>llm_description</code> 正则提取。前端"描述"列展示 <code>llm_description</code> 字段。</li>'
)
html = html.replace(
    '<li><strong><code>nodes/__init__.py</code> 未同步</strong>：只导出 5 个节点（init_doc, parse_params, product_support, src_content_extract, function_explanation_extract_node），未包含后续新增的 15 个节点（param_desc_extract, function_signature_extract, shape_extract, dtype_extract, dformat_extract, optional_extract, param_attr_extract, array_length_extract, allowed_range_extract, return_code_extract, determinism_extract, dtype_combo_extract, build_param_relations, build_param_constraint, assemble_result）和 param_relation_extract 子图。</li>',
    '<li><strong><code>nodes/__init__.py</code> 未同步</strong>：只导出 5 个节点（init_doc, parse_params, product_support, src_content_extract, function_explanation_extract_node），未包含后续新增/重构的节点（llm_description_extract, function_signature_extract, shape_extract, dtype_extract, dformat_extract, optional_extract, array_length_extract, allowed_range_extract, return_code_extract, determinism_extract, dtype_combo_extract, build_param_relations, build_param_constraint, assemble_result）和 param_relation_extract 子图。</li>'
)

# 14. Update sec-issue-code items
html = html.replace(
    '<li><strong><code>param_desc_extract_node</code> 字段填充不全</strong>：<code>_extract_one()</code> 中 <code>data_type</code>、<code>data_format</code>、<code>shape</code> 仍硬编码为空字符串（已由下游并行节点填充）；<code>parse_params.py</code> 使用内联 prompt 而非从 <code>prompts/__init__.py</code> 导入</li>',
    '<li><del><code>param_desc_extract_node</code> 字段填充不全</del> &check; 已修复 — 原节点已移除，由 <code>llm_description_extract</code> 替代。新节点一次 LLM 调用提取所有字段。<code>parse_params.py</code> 仍使用内联 prompt</li>'
)
html = html.replace(
    'shape_extract、dtype_extract、dformat_extract、optional_extract、array_length_extract、allowed_range_extract、return_code_extract、determinism_extract、dtype_combo_extract、param_relation_extract、build_param_constraint 各自 Semaphore(5)，并行时实际 LLM 调用峰值可达 55',
    'llm_description_extract、shape_extract、dtype_extract、dformat_extract、optional_extract、array_length_extract、allowed_range_extract、return_code_extract、determinism_extract、dtype_combo_extract、param_relation_extract、build_param_constraint 各自 Semaphore(5)，并行时实际 LLM 调用峰值可达 50'
)

# 15. Update prompt count
html = html.replace(
    '18个Prompt: PRODUCT_SUPPORT, SRC_CONTENT, PARAM_DESC, SHAPE, DTYPE, DFORMAT, OPTIONAL, FUNCTION_SIGNATURE_EXTRACT, FUNCTION_EXPLANATION_EXTRACT, ARRAY_LENGTH_EXTRACT, ALLOWED_RANGE_EXTRACT, RETURN_CODE_EXTRACT, DETERMINISM_EXTRACT, DTYPE_COMBO_TABLE, DTYPE_CONSTRAINT_TEXT, SHAPE_TO_DIMENSIONS, ALLOWED_RANGE_VALUE_BUILD, RELATION_OBJECT_BUILD',
    '19个Prompt: LLM_DESCRIPTION_EXTRACT, PRODUCT_SUPPORT, SHAPE, DTYPE, DFORMAT, OPTIONAL, FUNCTION_SIGNATURE_EXTRACT, FUNCTION_EXPLANATION_EXTRACT, ARRAY_LENGTH_EXTRACT, ALLOWED_RANGE_EXTRACT, RETURN_CODE_EXTRACT, DETERMINISM_EXTRACT, DTYPE_COMBO_TABLE, DTYPE_CONSTRAINT_TEXT, SHAPE_TO_DIMENSIONS, ALLOWED_RANGE_VALUE_BUILD, RELATION_OBJECT_BUILD (SRC_CONTENT + PARAM_DESC 已废弃)'
)

# 16. Update MCP communication pattern
html = html.replace(
    '整个 Pipeline 执行一次约产生 ~55 次子进程启动（param_relation_extract 子图额外增加 3~5 次，allowed_range_extract 额外增加 3~6 次，return_code_extract 额外增加 3~6 次，determinism_extract 额外增加 2~3 次，dtype_combo_extract 额外增加 2~3 次，build_param_relations 额外增加 3~5 次，build_param_constraint 额外增加 5~8 次，assemble_result 额外增加 10 次）。参数查询在 <code>src_content_extract</code> 中进行一次，下游节点通过 state 传递数据，避免重复 MCP 查询。',
    '整个 Pipeline 执行一次约产生 ~50 次子进程启动（llm_description_extract 额外增加 6~8 次，param_relation_extract 子图额外增加 3~5 次，allowed_range_extract 额外增加 3~6 次，return_code_extract 额外增加 3~6 次，determinism_extract 额外增加 2~3 次，dtype_combo_extract 额外增加 2~3 次，build_param_relations 额外增加 3~5 次，build_param_constraint 额外增加 5~8 次，assemble_result 额外增加 10 次）。参数列表在 <code>parse_params</code> 中创建，<code>llm_description_extract</code> 充实后通过 state 传递给下游，避免重复 MCP 查询。'
)

# 17. Update build_param_constraint description
html = html.replace(
    '汇总上游所有参数属性（shape、dtype、dformat、optional、param_attr、array_length、allowed_range 等），通过 LLM 二次处理',
    '汇总上游所有参数属性（shape、dtype、dformat、optional、array_length、allowed_range 等），通过 LLM 二次处理'
)

# 18. Update test count
html = html.replace(
    '测试（mcp_server/parsers 34 个 + agent 75 个）',
    '测试（mcp_server/parsers 34 个 + agent 95 个）'
)

# 19. Add new docs references
html = html.replace(
    '<tr><td>批量任务管理方案</td><td><code>docs/op-task.html</code></td><td>批量任务系统（tasks/task_items 表 + task_engine + API）方案文档</td></tr>',
    '<tr><td>批量任务管理方案</td><td><code>docs/op-task.html</code></td><td>批量任务系统（tasks/task_items 表 + task_engine + API）方案文档</td></tr>\n<tr><td>dimensions 数据流溯源</td><td><code>docs/dimensions-source.html</code></td><td>param_constraint.dimensions 从原始 .md 到 DB 的完整数据流</td></tr>\n<tr><td>dimensions 优化方案</td><td><code>docs/new-schema.html</code></td><td>shape_context 采集 + dimensions 平台无关化方案</td></tr>\n<tr><td>提取完整性建议</td><td><code>docs/suggestion.html</code></td><td>src_content 覆盖度 + param_relation 完整性优化建议</td></tr>'
)

# 20. Update API pipeline description
html = html.replace(
    'init_doc -> [product_support || parse_params || function_signature_extract || function_explanation_extract] -> src_content_extract -> param_desc_extract -> [shape_extract || dtype_extract || dformat_extract || optional_extract || param_attr_extract || array_length_extract || allowed_range_extract || return_code_extract || determinism_extract || dtype_combo_extract || param_relation_extract] -> build_param_relations -> build_param_constraint -> assemble_result',
    'init_doc -> [product_support || parse_params || function_signature_extract || function_explanation_extract] -> llm_description_extract -> [shape_extract || dtype_extract || dformat_extract || optional_extract || array_length_extract || allowed_range_extract || return_code_extract || determinism_extract || dtype_combo_extract || param_relation_extract] -> build_param_relations -> build_param_constraint -> assemble_result'
)

# Write
with open('docs/project_summary.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f'Updated: {len(html)} bytes, {html.count(chr(10))+1} lines')

# Verify
issues = []
for term in ['节点5a:', '节点5b:', '节点5c:', '节点5d:', '节点5e:', '节点5g:', '节点5h:', '节点5i:', '节点5j:', '节点5k:']:
    if term in html:
        issues.append(f'Stale node numbering: {term}')
if 'param_attr_extract' in html and '已移除' not in html and '已合并' not in html:
    issues.append('Stale param_attr_extract reference')

if issues:
    print(f'\nPotential issues ({len(issues)}):')
    for i in issues:
        print(f'  {i}')
else:
    print('No stale references detected.')