from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.types import StreamWriter

from LLM.Prompts import code_prompt

llm = ChatOpenAI(
    model="deepseek-v3",
    streaming=True,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)



# 节点1：校验输入是否为函数定义
system_msg = """

---

### **符合要求的输入必须满足以下条件**：
1. **包含明确的函数定义**：
   - 必须给出函数名称、返回值类型、参数列表。
   - 例如：`int is_prime(int n);`  
   
2. **包含详细的函数描述**：
   - 说明函数的具体功能、输入输出的含义、边界情况等。
   - 例如：“该函数用于判断一个整数是否为质数，输入一个整数 n，返回 1 表示是质数，返回 0 表示不是。”

3. **代码语言必须是 C 语言**：
   - 用户输入不能是 Python、Java、C++ 等其他语言的函数定义。

4. **输入必须是合理的 C 语言函数**：
   - 不能是过于模糊的描述，如“写一个计算数值的函数”。
   - 不能是单纯的代码片段（如`for (int i = 0; i < n; i++)`），必须是完整的函数定义。

5. **避免过于复杂或非标准的 C 语言结构**：
   - 不支持 C 语言标准库之外的自定义扩展（如 `__attribute__((constructor))` 之类的 GCC 特性）。
   - 不能是涉及内核编程、系统调用的低级代码（如 `inline assembly`）。

---

### **示例分析**
- **示例 1（符合要求）**  
**用户输入**：
函数名称：is_prime
返回值类型：int
参数：int n
描述：该函数用于判断一个整数是否为质数。输入一个整数 n，返回 1 表示是质数，返回 0 表示不是。
**返回**：
符合 C 语言函数级代码生成的要求。
- **示例 2（不符合要求 - 缺少函数定义）**  
**用户输入**：
这个函数用于检查一个数是否为质数。
**返回**：
不符合 C 语言函数级代码生成的要求，原因如下： 你的输入缺少完整的函数定义，包括函数名称、返回值类型和参数列表。请提供完整的函数信息，例如： 函数名称：is_prime
返回值类型：int
参数：int n
描述：[详细描述]
- **示例 3（符合要求）**  
**用户输入**：
int max(int num1, int num2)，输出上面函数的实现代码，该函数的功能为返回num1和num2中更大的那个。
- **示例 4（不符合要求 - 只包含定义，没有其他任何解释）**  
int max(int num1, int num2)
"""
user_prompt = """
1. **如果输入符合要求**（即提供了完整的函数定义及描述），请返回：符合 C 语言函数级代码生成的要求。
2. **如果输入不符合要求**，请返回：不符合 C 语言函数级代码生成的要求。
"""
def validate_task_input(state, writer: StreamWriter):
    writer({"custom_key": "正在进行输入判断..."})
    user_input = state["user_input"]
    messages = [
        SystemMessage(
            content= f"**任务：判断用户输入是否符合 C 语言函数级代码生成的要求**\n\n{system_msg}"
        ),
        HumanMessage(
            content=f"请判断这个输入是否符合函数级代码生成的要求：'{user_input}'\n\n{user_prompt}"
        )
    ]
    response = llm.invoke(messages)
    valid = "不符合" in response.content
    return {**state, "valid": not valid}

# 节点2：生成函数代码
def code_generation_task(state):
    user_input = state["user_input"]
    subflow = code_prompt.create_subflow()
    input_data = {
        "function_definition": user_input,
    }
    response = subflow.invoke(input_data)

    return {**state, "code": response["code"]}

# 节点3：如果验证失败，直接返回错误信息
def reject_task(state, writer: StreamWriter):
    writer({"custom_key": "输入不符合函数级代码生成要求，请根据修改建议修改后重新输入。"})
    user_input = state["user_input"]
    messages = [
        SystemMessage(
            content=f"**任务：根据下面的介绍分析用户输入不符合函数级代码生成的原因，并给出修改方案**\n\n{system_msg}"
        ),
        HumanMessage(
            content=f"请分析用户输入给出不符合函数级代码生成的原因和修改方案：'{user_input}'\n\n{user_prompt}"
        )
    ]
    response = llm.invoke(messages)

    return {**state, "tasks": "输入不符合任务分解要求，请重新输入。\n\n" + response.content}

# 决策函数
def decision_task(state):
    return "code_gen" if state["valid"] else "reject"

# 定义工作流
def build_task_graph():
    graph_builder = StateGraph(dict)
    graph_builder.add_node("validate", validate_task_input)
    graph_builder.add_node("code_gen", code_generation_task)
    graph_builder.add_node("reject", reject_task)

    graph_builder.set_entry_point("validate")
    graph_builder.add_conditional_edges("validate", decision_task, {
        "code_gen": "code_gen",
        "reject": "reject"
    })

    graph_builder.add_edge("code_gen", END)
    graph_builder.add_edge("reject", END)

    return graph_builder.compile()

# 创建流程图
task_graph = build_task_graph()

# 流程图的调用
def chat(message):
    inputs = {
        "user_input": message[-1]['content'],
        "valid": False,
        "code": "",
    }
    for stream_mode, chunk in task_graph.stream(
            inputs,
            stream_mode=["messages", "custom"],
    ):
        # print(chunk)
        if 'custom_key' in chunk:
            # print(chunk["custom_key"])
            yield chunk["custom_key"] + '\n'
        else:
            message_chunk, metadata = chunk
            content = message_chunk.content
            if metadata['langgraph_node'] in ['gen', 'reject'] and content:
                # print(content, end="", flush=True)
                yield content

def _run_task_decomposition(uid: str, chat_id: str, user_input: str):
    inputs = {
        "uid": uid,
        "chat_id": chat_id,
        "user_input": user_input,
        "valid": False,
        "code": "",
    }
    # result =  task_graph.invoke(inputs)
    # print(result)
    # return result["tasks"]
    # 流式输出
    for stream_mode, chunk in task_graph.stream(
        inputs,
        stream_mode=["messages", "custom"],
    ):
        # print(chunk)
        if 'custom_key' in chunk:
            print(chunk["custom_key"])
            # yield chunk["custom_key"]
        else:
            message_chunk, metadata = chunk
            content = message_chunk.content
            if metadata['langgraph_node'] in ['gen', 'reject'] and content:
                print(content, end="", flush=True)
                # yield content

# 示例调用（async）
if __name__ == "__main__":
    # _run_task_decomposition("u123", "chat001", "设计一个函数，找到列表中的最大值。")
    input = """
函数名称：find_max
返回值类型：int
参数：int arr[], int size
描述：该函数用于找到整数数组中的最大值。输入一个整数数组 `arr` 和数组的大小 `size`，返回数组中的最大值。
"""
    _run_task_decomposition("u123", "chat001", input)