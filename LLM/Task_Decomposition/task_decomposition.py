from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Union
import asyncio

from langgraph.types import StreamWriter

import LLM.Prompts.task_prompt as task_prompt
from LLM.llm_manager import llm_stream


# 定义状态结构
class TaskState(TypedDict):
    uid: str
    chat_id: str
    user_input: str
    valid: bool
    tasks: Union[List[str], str]  # 分解结果或错误信息


# 初始化 LLM
llm = ChatOpenAI(
    model="deepseek-v3",
    streaming=True,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)


# 节点1：校验输入是否为可分解任务
def validate_task_input(state: TaskState, writer: StreamWriter) -> TaskState:
    writer({"custom_key": "正在进行输入判断..."})
    user_input = state["user_input"]
    messages = [
        HumanMessage(
            content=f"请判断这个输入是否是一个编程任务，并且可以被分解为多个编程子任务，仅回答 是 或 否：'{user_input}'"
        )
    ]
    response = llm.invoke(messages)
    valid = "是" in response.content
    return {**state, "valid": valid}


# 节点2：分解任务
def decompose_task(state: TaskState) -> TaskState:
    user_input = state["user_input"]
    subflow = task_prompt.create_subflow()
    input_data = {
        "problem_description": user_input,
    }
    # 调用子流程进行任务分解
    response = subflow.invoke(input_data)
    tasks = response["function_code"]
    return {**state, "tasks": tasks}

    # messages = [
    #     HumanMessage(
    #         content=f"请将下面的任务输入分解为多个子任务，并以列表形式返回：'{user_input}'"
    #     )
    # ]
    # chunks = []
    # async for chunk in llm.astream(messages):
    #     if chunk.content:
    #         chunks.append(chunk.content)
    #         print(chunk.content, end="", flush=True)  # 流式输出
    #
    # return {**state, "tasks": ''.join(chunks)}


# 节点3：如果验证失败，直接返回错误信息
def reject_task(state: TaskState, writer: StreamWriter) -> TaskState:
    writer({"custom_key": "输入不符合任务分解要求，请重新输入。"})
    return {**state, "tasks": "输入不符合任务分解要求，请重新输入。"}

# 决策函数
def should_decompose(state: TaskState) -> str:
    return "decompose" if state["valid"] else "reject"


# 构建 LangGraph 流程图
def build_task_graph():
    graph_builder = StateGraph(TaskState)

    # 添加节点
    graph_builder.add_node("validate", validate_task_input)
    graph_builder.add_node("decompose", decompose_task)
    graph_builder.add_node("reject", reject_task)

    # 添加边
    graph_builder.set_entry_point("validate")
    graph_builder.add_conditional_edges("validate", should_decompose, {
        "decompose": "decompose",
        "reject": "reject"
    })

    # 结束点
    graph_builder.add_edge("decompose", END)
    graph_builder.add_edge("reject", END)

    return graph_builder.compile()


# 创建流程图
task_graph = build_task_graph()


# 使用函数（调用者）
def _run_task_decomposition(uid: str, chat_id: str, user_input: str):
    inputs = {
        "uid": uid,
        "chat_id": chat_id,
        "user_input": user_input,
        "valid": False,
        "tasks": "",
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
            if metadata['langgraph_node'] == 'func' and content:
                print(content, end="", flush=True)
                # yield content

def chat(message):
    # print(message)
    inputs = {
        "user_input": message[-1]['content'],
        "valid": False,
        "tasks": "",
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
            if metadata['langgraph_node'] == 'func' and content:
                # print(content, end="", flush=True)
                yield content


# 示例调用（async）
if __name__ == "__main__":
    _run_task_decomposition("u123", "chat001", "设计一个函数，找到列表中的最大值。")
