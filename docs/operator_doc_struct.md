# 算子文档结构化拆分设计

## 文档标题层级分析

以 `aclnnBatchNormElemt.md` 为例，典型的算子文档标题层级如下：

```
# aclnnBatchNormElemt              ← 算子名 (H1)
## 产品支持情况                      ← 无标题标记，表格块
## 功能说明                          ← 公式
## 函数原型                          ← 两段式签名
## aclnnBatchNormElemtGetWorkspaceSize  ← 第一段接口
   - 参数说明 (表格)
   - 返回值 (错误码表)
## aclnnBatchNormElemt              ← 第二段接口
   - 参数说明
   - 返回值
## 约束说明                          ← 约束
## 调用示例                          ← C++代码
```

## 数据模型

```python
from pydantic import BaseModel
from enum import Enum


class SectionType(str, Enum):
    HEADER = "header"                # 算子标题 + 元信息
    PRODUCT_SUPPORT = "product_support"  # 产品支持矩阵
    DESCRIPTION = "description"      # 功能说明 + 计算公式
    PROTOTYPE = "prototype"          # 函数签名
    PARAMS_GET_WORKSPACE = "params_get_workspace"  # 第一段接口参数表
    RETURN_CODES_GET_WORKSPACE = "return_codes_get_workspace"  # 第一段错误码
    PARAMS_EXECUTE = "params_execute"      # 第二段接口参数表
    RETURN_CODES_EXECUTE = "return_codes_execute"
    CONSTRAINTS = "constraints"      # 约束说明
    EXAMPLE = "example"              # 调用示例代码


class RawSection(BaseModel):
    """拆分后的单个文档片段"""
    section_type: SectionType        # 语义类型
    heading: str | None = None       # 原始标题文本
    level: int                       # markdown 标题层级 (1-6)
    content: str                     # 原始 markdown 文本（含表格、代码块）
    line_start: int                  # 在原文中的起始行号
    line_end: int                    # 在原文中的结束行号


class SplitDocument(BaseModel):
    """一份算子文档拆分后的完整结构"""
    operator_name: str               # 算子名，如 "aclnnBatchNormElemt"
    source_file: str                 # 原始文件路径
    cann_version: str | None = None  # 如 "CANN社区版9.0.0"
    sections: list[RawSection]       # 有序片段列表
```

## 拆分策略

按标题层级切，但**识别语义类型**不能纯靠标题文本匹配，建议两层策略：

| 层 | 策略 | 示例 |
|---|---|---|
| H1 | 固定取算子名 + URL 元信息 | `# aclnnBatchNormElemt` |
| H2 文本匹配 | 标题关键词 → `SectionType` | "功能说明"→ `description`，"约束"→ `constraints` |
| H2 无标题表格 | 前一个 H2 之后、下一个 H2 之前的内容归入 `product_support` | 产品支持表格 |
| H3 "参数说明" | 归属到父级 H2 对应的类型 | `params_get_workspace` 或 `params_execute` |
| H3 "返回值" | 同上 | `return_codes_*` |

## 拆分后用途映射

后续调用 LLM 时，按需选片段输入：

| 任务 | 需要的 SectionType |
|---|---|
| 提取参数约束 (shape/dtype/format) | `params_get_workspace` |
| 提取错误码 → 校验规则 | `return_codes_get_workspace` |
| 生成测试用例 | `params_*` + `constraints` + `description` |
| 生成调用代码 | `prototype` + `example` |

每个任务只喂相关片段，减少 token 消耗，降低 LLM 干扰。
