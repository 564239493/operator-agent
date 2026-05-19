# aclnnTestOp-CANN社区版8.0.0-昇腾社区

**URL:** https://example.com/test.md

**Saved:** 2026-01-01

---

## aclnnTestOp

[📄 查看源码](https://example.com/test)

##

产品支持情况

| 产品 | 是否支持  |
|---|---|
| Atlas A2 训练系列产品 | √  |
| Atlas 推理系列产品 | ×  |

##

功能说明

-   接口功能：测试算子描述。

-   计算公式：y = x + 1

##

函数原型

每个算子分为两段式接口。

```
aclnnStatus aclnnTestOpGetWorkspaceSize(
  const aclTensor* input,
  aclTensor*       output,
  uint64_t*        workspaceSize,
  aclOpExecutor**  executor)
```

```
aclnnStatus aclnnTestOp(
  void             *workspace,
  uint64_t          workspaceSize,
  aclOpExecutor    *executor,
  const aclrtStream stream)
```

##

aclnnTestOpGetWorkspaceSize

-   **参数说明**

    | 参数名 | 输入/输出 | 描述 | 使用说明 | 数据类型 | 数据格式 | 维度(shape) | 非连续Tensor  |
    |---|---|---|---|---|---|---|---|
    | input（aclTensor*） | 输入 | 测试输入。 | 支持空Tensor。 | FLOAT32、FLOAT16 | ND | 2-4 | √  |
    | output（aclTensor*） | 输出 | 测试输出。 | 数据类型与input一致。 | FLOAT32、FLOAT16 | ND | 2-4 | √  |
    | workspaceSize（uint64\_t\*） | 输出 | workspace大小。 | \- | \- | \- | \- | \-  |
    | executor（aclOpExecutor\*\*） | 输出 | op执行器。 | \- | \- | \- | \- | \-  |

-   **返回值**

    aclnnStatus

    | 返回码 | 错误码 | 描述  |
    |---|---|---|
    | ACLNN\_ERR\_PARAM\_NULLPTR | 161001 | 传入的指针类型入参是空指针。  |
    | ACLNN\_ERR\_PARAM\_INVALID | 161002 | input数据类型不在支持范围。  |

##

aclnnTestOp

-   **参数说明**

    | 参数名 | 输入/输出 | 描述  |
    |---|---|---|
    | workspace | 输入 | Device侧workspace。  |
    | workspaceSize | 输入 | workspace大小。  |
    | executor | 输入 | op执行器。  |
    | stream | 输入 | 执行任务的Stream。  |

##

约束说明

-   input必须为FLOAT32或FLOAT16。

##

调用示例

```
#include <iostream>
int main() {
    std::cout << "hello" << std::endl;
    return 0;
}
```
