from http.client import responses

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.types import StreamWriter

from LLM.Prompts import code_prompt, test_prompt

llm = ChatOpenAI(
    model="deepseek-v3",
    streaming=True,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

def validate_task_input(state, writer: StreamWriter):
    writer({"custom_key": "正在进行输入判断..."})
    user_input = state["user_input"]
    messages = [
        SystemMessage(
            content= f"**任务：用户希望让大模型根据输入的C语言函数生成测试用例，所以需要你判断用户的输入是否为 C 语言的函数代码，如果是请返回“是”，如果不是请返回“否”，不要返回其他任何内容**\n\n"
        ),
        HumanMessage(
            content=f"请判断下面的代码是不是C语言函数：'{user_input}'\n\n"
        )
    ]
    response = llm.invoke(messages)
    valid = "否" in response.content
    return {**state, "valid": not valid}

# 节点：如果验证失败，直接返回错误信息
def reject_task(state, writer: StreamWriter):
    writer({"custom_key": "输入不符合函数级代码的要求，请根据修改建议修改后重新输入。"})
    user_input = state["user_input"]
    messages = [
        SystemMessage(
            content=f"**任务：根据下面的介绍分析用户输入不是C语言函数级代码的原因，并给出修改方案**\n\n"
        ),
        HumanMessage(
            content=f"请分析用户输入给出不是C语言函数级代码的原因和修改方案：'{user_input}'\n\n"
        )
    ]
    response = llm.invoke(messages)

    return {**state, "tasks": "输入不符合测试样例生成的要求，请重新输入。\n\n" + response.content}

# 决策函数
def decision_task(state):
    return "continue" if state["valid"] else "reject"

# 节点：生成测试样例
def test_generation_task(state):
    user_input = state["user_input"]
    subflow = test_prompt.create_subflow()
    input = {"messages": [{"role": "user", "content": user_input}]}
    response = subflow.invoke(input)

    return {**state, "tasks": response["messages"][-1].content}  # 返回最后一条消息的内容

# 定义工作流
def build_task_graph():
    """创建工作流"""
    graph_builder = StateGraph(dict)
    graph_builder.add_node("validate_task_input", validate_task_input)
    graph_builder.add_node("reject_task", reject_task)
    graph_builder.add_node("test_generation_task", test_generation_task)

    # 设置起始节点
    graph_builder.set_entry_point("validate_task_input")

    # 添加条件边
    graph_builder.add_conditional_edges(
        "validate_task_input",
        decision_task,
        {"continue": "test_generation_task", "reject": "reject_task"},
    )

    # 添加结束节点
    graph_builder.add_edge("test_generation_task", END)
    graph_builder.add_edge("reject_task", END)

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
            if metadata['langgraph_node'] in ['generate', 'reject_task'] and content:
                # print(content, end="", flush=True)
                yield content

if __name__ == "__main__":
    # 测试代码
    input = """
    // 判断一个数是否为质数
    bool is_prime(int n) {
        if (n <= 1) return false;
        for (int i = 2; i * i <= n; i++) {
            if (n % i == 0) return false;
        }
        return true;
    }
    """
    task_graph = build_task_graph()
    for stream_mode, chunk in task_graph.stream(
            {
                "user_input": input,
            },
            stream_mode=["messages", "custom"],
    ):
        if 'custom_key' in chunk:
            print(chunk["custom_key"] + '\n')
        else:
            message_chunk, metadata = chunk
            content = message_chunk.content
            if metadata['langgraph_node'] in ['generate', 'reject_task'] and content:
                print(content, end="", flush=True)