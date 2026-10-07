# 从最小 agent 开始

这个版本接收一个任务，使用 OpenAI Responses API，让模型选择工具，由 Python 执行工具，把结果交回模型，直到模型给出答案。当前只有 `add(a, b)`，核心代码在 `agent.py`。

## 运行第一版

从 GitHub 克隆项目并进入目录：

```sh
git clone https://github.com/GTilor/mini-agent.git
cd mini-agent
```

如果已经有本地项目，直接进入现有项目目录。首次安装环境：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

在运行程序的同一个终端里配置你的 OpenAI API 密钥：

```sh
export OPENAI_API_KEY='替换为你自己的 API 密钥'
```

默认使用 `gpt-5.4-mini`。如果要更换模型，可设置 `OPENAI_MODEL`，所选模型需要支持 Responses API 和函数工具。

运行：

```sh
.venv/bin/python agent.py
```

先输入一个小任务：

```text
请用 add 工具计算 3 + 8。
```

然后试试需要依赖前一步结果的任务：

```text
先用 add 工具计算 3 + 8，再把工具返回的结果加上 10。
```

可能看到的流程如下。这是示意，真实模型的调用次数、参数形式和回答措辞可能不同：

```text
[第 1 轮] 请求模型
[工具] add 参数={"a":3,"b":8} 结果=11
[第 2 轮] 请求模型
[工具] add 参数={"a":11,"b":10} 结果=21
[第 3 轮] 请求模型

回答： 最终结果是 21。
```

程序最多请求模型 6 轮；到达上限会报告任务未完成。一次工具调用出错时，错误会被交回模型，模型可以在剩余轮数内修正参数。每次启动处理一个新任务。

## 顺着一个输入读代码

| 部分 | 输入 | 输出或用途 |
|---|---|---|
| `add` | 数字 `3`、`8` | 数字 `11` |
| `TOOLS` | 我们填写的工具名称、用途、参数规则 | 发给模型的工具说明 |
| `TOOL_FUNCTIONS` | 工具名 `"add"` | 找到本地 Python 函数 `add` |
| `history` | 用户问题、模型输出、工具结果 | 下一次请求所需的上下文 |
| `run_agent` | 一个任务 | 模型依据工具结果组织的答案 |

`json.loads(call.arguments)` 把模型返回的 JSON 参数文本变成 Python 字典。例如，文本 `'{"a":3,"b":8}'` 变成字典 `{"a": 3, "b": 8}`。

`function(**arguments)` 把字典里的字段作为命名参数传给函数。在这个例子里，它等同于 `add(a=3, b=8)`。这使不同工具都能通过同一段循环调用。

`call_id` 是模型这次工具调用的标识。把结果交回模型时，带上同一个标识，模型就能知道结果对应哪一次请求。

`history.extend(response.output)` 保留模型返回的全部输出；工具结果也追加到同一个列表。下一轮模型因此能够看到前一步请求了什么、实际得到了什么。

## 第一次扩展：添加乘法工具

在 `run_agent` 的定义之前，加入下面这段。它包含一个执行函数、一项注册和一份工具说明：

```python
def multiply(a, b):
    return a * b


TOOL_FUNCTIONS["multiply"] = multiply

TOOLS.append(
    {
        "type": "function",
        "name": "multiply",
        "description": "计算两个数字相乘的结果。",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["a", "b"],
            "additionalProperties": False,
        },
        "strict": True,
    }
)
```

新工具的返回值先使用数字、文本、列表或字典，方便转换成 JSON 后交回模型。

核心循环能够按工具名找到新函数。运行时输入：

```text
先用 add 计算 3 + 8，再用 multiply 将返回的结果乘以 4。
```

检查工具日志：加法应返回 `11`，乘法应返回 `44`。这样就能确认新增的功能接入了整个流程。

## 逐步增加能力

一次只增加一项，给它准备一个小输入，观察实际工具日志和输出。

| 阶段 | 增加什么 | 用什么小任务确认 |
|---|---|---|
| 1 | 新工具，例如乘法、读取当前时间 | 查看模型选了哪个工具、传了哪些参数 |
| 2 | 多轮对话，保留同一次会话的 `history` | 第一句算 `3+8`，第二句问“刚才结果再加 10” |
| 3 | 项目笔记的读取与搜索工具 | 让它从一份短笔记中找出指定内容，并标明来源 |
| 4 | 会话保存与恢复 | 退出程序，再加载之前的对话继续任务 |
| 5 | 一组固定任务作为回归检查 | 改功能后，确认原有任务仍能完成 |

工具越来越多时，可以把执行函数和工具说明移到 `tools.py`；处理模型请求的方式可以单独放进 `model.py`。目前同一个文件方便顺着数据流阅读。

## 接口来源与验证范围

- [OpenAI 函数工具与结果回传流程](https://developers.openai.com/api/docs/guides/function-calling)
- [Python SDK 安装与环境变量配置](https://developers.openai.com/api/docs/libraries)
- [GPT-5.4 Mini 支持的接口与能力](https://developers.openai.com/api/docs/models/gpt-5.4-mini)

初始版本使用 OpenAI SDK 2.48.0。此前使用真实 SDK 连接本地模拟接口，验证了连续调用、同一轮多个调用、完整上下文保留、工具错误回传与修正、结束条件、轮数上限，以及上面的乘法扩展示例。

这些检查使用模拟模型响应。真实模型是否选择了正确工具，以及账号、网络和模型访问权限，需要配置密钥后用上面的两个小任务验证。
