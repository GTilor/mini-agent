"""最小 agent：模型选择工具，Python 执行，把结果交回模型。"""

import json
import os

from openai import OpenAI


# 1. 真正执行工作的 Python 函数。
def add(a, b):
    return a + b


# 2. 程序用这张表，把模型返回的工具名对应到 Python 函数。
TOOL_FUNCTIONS = {"add": add}


# 3. 发给模型的工具说明。
TOOLS = [
    {
        "type": "function",
        "name": "add",
        "description": "计算两个数字相加的结果。",
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
]

INSTRUCTIONS = (
    "你是一个使用工具完成任务的中文助手。"
    "遇到工具可以完成的操作时，调用相应工具。"
    "涉及多步计算时，按依赖关系分步调用，依据工具实际返回值继续。"
    "工具报错时，可以修正参数后重试。任务完成后，用中文简洁回答。"
)


# 4. agent 的核心循环。
def run_agent(question, client, model, max_rounds=6):
    history = [{"role": "user", "content": question}]

    for round_index in range(max_rounds):
        print(f"[第 {round_index + 1} 轮] 请求模型")
        response = client.responses.create(
            model=model,
            instructions=INSTRUCTIONS,
            input=history,
            tools=TOOLS,
        )

        if response.status != "completed":
            raise RuntimeError(f"模型响应未完成：{response.status}")

        # 保留模型返回的所有内容，包括工具调用及推理项。
        history.extend(response.output)

        tool_calls = []
        for item in response.output:
            if item.type == "function_call":
                tool_calls.append(item)

        # 模型给出文字答案后，结束这个任务。
        if not tool_calls:
            if not response.output_text:
                raise RuntimeError("模型没有返回文字答案。")
            return response.output_text

        for call in tool_calls:
            try:
                arguments = json.loads(call.arguments)
                function = TOOL_FUNCTIONS[call.name]
                # 例如 function(**{"a": 3, "b": 8}) 等同于 add(a=3, b=8)。
                result = function(**arguments)
            except Exception as error:
                result = {"error": str(error)}

            print(f"[工具] {call.name} 参数={call.arguments} 结果={result}")
            history.append(
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result, ensure_ascii=False),
                }
            )

    raise RuntimeError(f"达到 {max_rounds} 轮上限，任务尚未完成。")


if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("请先配置 OPENAI_API_KEY，步骤见 README.md。")

    model = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")
    client = OpenAI(timeout=30.0, max_retries=0)
    question = input("任务：").strip()
    if question:
        answer = run_agent(question, client, model)
        print("\n回答：", answer)
