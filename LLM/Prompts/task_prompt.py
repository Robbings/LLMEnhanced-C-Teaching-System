# file_name = task_prompt.py
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langgraph.graph import START, MessagesState
from langgraph.graph import StateGraph
from langgraph.types import StreamWriter
from sympy import false
from LLM.llm_manager import get_llm_stream, get_llm_no_stream

from LLMEnhanced_C_Teaching_System.settings import LLM_MODEL

system_prompt_deco ="""
You are a code reasoning assistant. 
Your task is to analyze the given programming problem and generate a modular reasoning graph 
(Multi-Level Reasoning Graph, MLR Graph) to guide the code generation process.
Provide your reasoning in the following hierarchical textual format clearly:
###  Format
H1 [High-Level]: Solve the problem: {{Problem description}}
  Reasoning: Break the problem into major tasks: {{High-level task 1}} and {{High-level task 2}}.
  ├── H1.1 [High-Level]: {{Subtask 1 of High-Level}}
  │       Reasoning: {{Reasoning for subtask 1}}
  │       ├── I1.1 [Intermediate-Level]: {{Intermediate-level task 1 for subtask 1}}
  │       │         Reasoning: {{Reasoning for intermediate-level task 1}}
  │       └── I1.2 [Intermediate-Level]: {{Intermediate-level task 2 for subtask 1}}
  │                 Reasoning: {{Reasoning for intermediate-level task 2}}
  ├── H1.2 [High-Level]: {{Subtask 2 of High-Level}}
  │       Reasoning: {{Reasoning for subtask 2}}
  │       ├── I2.1 [Intermediate-Level]: {{Intermediate-level task 1 for subtask 2}}
  │       │         Reasoning: {{Reasoning for intermediate-level task 1}}
  │       │         └── D2.1 [Detailed-Level]: {{Detailed implementation details or pseudo-code}}
"""

system_prompt_gen = """
You are a code generation assistant. Your task is to generate C language function definitions that adhere strictly to the C standard based on the given modular reasoning (MLR graph).
The generated code must be modular and well-structured, consisting only of function definitions with appropriate comments.
Each function should have a clear and specific purpose, following best practices in C programming. You must only output the C language function definitions.
Warning: Output only the definition of the function, not the implementation of the function.

---

下面是一个拥有良好结构的 C 函数定义示例：

```c
// 总任务：判断给定整数是否为质数

// 1. 读取输入
int read_input();  // 读取整数输入

// 2. 判断是否为质数
int is_prime(int n);  // 返回 1 表示质数，0 表示非质数

// 3. 输出结果
void print_result(int is_prime);  // 根据布尔值输出 "YES" 或 "NO"

int main() {{
    int n = read_input();
    int prime_flag = is_prime(n);
    print_result(prime_flag);
    return 0;
}}
```

---

你生成的函数定义必须满足以下规则和原则，同时尽可能遵循以下的建议：

##### 原则

1. 一个函数仅完成一件功能

2. 重复代码应该尽可能提炼成函数。

##### 规则

1. 避免函数过长，新增函数不超过50行（非空非注释行）。

2. 避免函数的代码块嵌套过深，新增函数的代码块嵌套不超过4层。

3. 设计高扇入，合理扇出（小于7）的函数。

> 说明：扇出是指一个函数直接调用（控制）其它函数的数目，而扇入是指有多少上级函数调用它。

##### 建议

1. 函数的参数个数不超过5个。

2. 除打印类函数外，不要使用可变长参函数。

3. 函数命名应以函数要执行的动作命名，一般采用动词或者动词＋名词的结构。

> 示例：找到当前进程的当前目录
>
> ```DWORD GetCurrentDirectory( DWORD BufferLength, LPTSTR Buffer );```

4. 函数指针除了前缀，其他按照函数的命名规则命名。

"""

user_prompt_gen = """
Modular Reasoning (MLR graph): {mlr_graph}
Output: Provide only the complete code corresponding to the given modular reasoning.Should contain Main function. If possible, organize the code into multiple modular functions.
"""

graph_prompt_template = ChatPromptTemplate([
    ("system", system_prompt_deco),
    ("user", "Please analyze the following programming problem: {problem_description}"),
])

func_prompt_template = ChatPromptTemplate([
    ("system", system_prompt_gen),
    ("user", user_prompt_gen),
])


def graph_node(state, writer: StreamWriter):
    """Graph node for generating the reasoning graph."""
    writer({"custom_key": "正在生成 MLR 图..."})

    # 正式生成
    messages = graph_prompt_template.format_messages(problem_description=state["problem_description"])
    llm = get_llm_stream()
    response = llm.invoke(messages)

    # 返回新的状态（注意这里不能再yield了，要return最终结果）
    return {**state, "mlr_graph": response.content}


def func_node(state):
    """Graph node for generating the function code."""
    messages = func_prompt_template.format_messages(mlr_graph=state["mlr_graph"])
    llm = get_llm_stream()
    response = llm.invoke(messages)
    # 全部完成后，返回最终结果
    return {**state, "function_code": response.content}


def create_subflow():
    """Create a subflow for task decomposition and function generation."""
    graph_builder = StateGraph(dict)
    graph_builder.add_node("graph", graph_node)
    graph_builder.add_node("func", func_node)

    graph_builder.set_entry_point("graph")
    graph_builder.add_edge("graph", "func")
    graph_builder.set_finish_point("func")

    subflow = graph_builder.compile()
    return subflow


# if __name__ == "__main__":
#     # 测试
#     subflow = create_subflow()
#
#     input_data = {
#         "problem_description": "Design a function that finds the maximum number in a list.",
#     }
#     for stream_mode, chunk in subflow.stream(
#             input_data,
#             stream_mode=["messages", "custom"],
#     ):
#         if 'custom_key' in chunk:
#             print(chunk["custom_key"] + '\n')
#         else:
#             message_chunk, metadata = chunk
#             content = message_chunk.content
#             if content:
#                 print(content, end="", flush=True)
#
#
#         # print(f"Stream mode: {stream_mode}")
#         # print(chunk)
#         # print("\n")