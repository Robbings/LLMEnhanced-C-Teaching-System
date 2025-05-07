from langgraph.graph import StateGraph
from langgraph.types import StreamWriter
from langchain_core.prompts import ChatPromptTemplate

from LLM.llm_manager import get_llm_stream

system_prompt_deco = """
Here is an example：
Please understand the requirement and write a rough solvingprocess. It starts with a input-output structure. You should use three basic structures to build the solving process, including sequences, branches, and loops. The necessary details should be written in natural languages.

### Problem
//Write a C function to find the first repeated character in a given string.
char firstRepeatedChar(const char *str);

### SCoT
Input: str: a string
Output: ch: a repeated character in str
1: for each character ch in str:
2:   if ch appears more than once in str:
3:     return ch
4: return None

Please understand the requirement and write a rough solvingprocess. It starts with a input-output structure. You should use three basic structures to build the solving process, including sequences, branches, and loops. The necessary details should be written in natural languages.
"""

user_prompt_deco = """
Here is the problem, Please only provide its SCoT:
{function_definition}
"""

system_prompt_gen = """
请根据函数定义和solvingprocess，生成一个完整的函数实现代码。请注意，函数的输入和输出类型必须与函数定义中的类型一致。请确保代码没有语法错误，并添加丰富的中文注释。
"""

user_prompt_gen = """
这是函数的定义：
{function_definition}
这是solvingprocess：
{solvingprocess}
"""

scot_prompt_template = ChatPromptTemplate([
    ("system", system_prompt_deco),
    ("user", user_prompt_deco),
])

gen_prompt_template = ChatPromptTemplate([
    ("system", system_prompt_gen),
    ("user", user_prompt_gen),
])

def scot_node(state, writer: StreamWriter):
    """生成SCoT"""
    writer({"custom_key": "正在生成 SCoT 流程..."})
    function_definition = state["function_definition"]
    prompt = scot_prompt_template.format_prompt(function_definition=function_definition)
    llm = get_llm_stream()
    response = llm.invoke(prompt)
    return {**state, "solvingprocess": response.content}

def gen_node(state, writer: StreamWriter):
    """生成代码"""
    function_definition = state["function_definition"]
    solvingprocess = state["solvingprocess"]
    prompt = gen_prompt_template.format_prompt(function_definition=function_definition, solvingprocess=solvingprocess)
    llm = get_llm_stream()
    response = llm.invoke(prompt)
    return {**state, "code": response.content}

def create_subflow():
    """创建子流程"""
    code_generation_flow = StateGraph(dict)

    code_generation_flow.set_entry_point("scot")
    code_generation_flow.add_edge("scot", "gen")
    code_generation_flow.set_finish_point("gen")

    code_generation_flow.add_node("scot", scot_node)
    code_generation_flow.add_node("gen", gen_node)

    return code_generation_flow.compile()

if __name__ == "__main__":
    # 测试代码
    function_definition = "char firstRepeatedChar(const char *str);"
    code_generation_flow = create_subflow()
    for stream_mode, chunk in code_generation_flow.stream(
            {
                "function_definition": function_definition,
            },
            stream_mode=["messages", "custom"],
    ):
        if 'custom_key' in chunk:
            print(chunk["custom_key"] + '\n')
        else:
            message_chunk, metadata = chunk
            content = message_chunk.content
            if content:
                print(content, end="", flush=True)