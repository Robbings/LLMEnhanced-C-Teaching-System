import os
from logging import Logger

from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools.retriever import create_retriever_tool
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState
from langgraph.types import StreamWriter

from LLM.Func_Code_Generation.code_generation import user_prompt
from LLM.llm_manager import get_llm_stream, get_llm_use_tool_stream
from langgraph.graph import END
from langgraph.prebuilt import ToolNode, tools_condition

from LLMEnhanced_C_Teaching_System.settings import PROJECT_PATH

system_prompt_unity = """
You are a helpful assistant that helps me to write unit tests for C code using Unity Test framework.Please retrieve before answer.
Unity Test is a unit testing framework built for C, with a focus on working with embedded toolchains.

The requirements are as follows:
1. You need to write unit tests for the C code I provide.
2. You need to use the Unity Test framework.
3. The test samples should cover all possible branches and situations.
4. add annotations to the test code using chinese.
5. you can use tools to help you write the test code.
6. Try to generate the test values using expressions or code instead of directly using constants.

When you're done, your test file will look something like this:

```c
#include "unity.h"
#include "file_to_test.h"

void setUp(void) {{
    // set stuff up here
}}

void tearDown(void) {{
    // clean stuff up here
}}

void test_function_should_doBlahAndBlah(void) {{
    //test stuff
}}

void test_function_should_doAlsoDoBlah(void) {{
    //more test stuff
}}

// not needed when using generate_test_runner.rb
int main(void) {{
    UNITY_BEGIN();
    RUN_TEST(test_function_should_doBlahAndBlah);
    RUN_TEST(test_function_should_doAlsoDoBlah);
    return UNITY_END();
}}
```
"""

system_prompt_unity_retrieve = """
It's possible that you will need more customization than this, eventually. For that sort of thing, you're going to want to look at the configuration guide. This should be enough to get you going, though.

you can get more knowledge about this framework by read documents, blow is the brief introduction:
Unity Assertions reference
This document will guide you through all the assertion options provided by Unity. This is going to be your unit testing bread and butter. You'll spend more time with assertions than any other part of Unity.

Unity Assertions Cheat Sheet
This document contains an abridged summary of the assertions described in the previous document. It's perfect for printing and referencing while you familiarize yourself with Unity's options.

Unity Configuration Guide
This document is the one to reference when you are going to use Unity with a new target or compiler. It'll guide you through the configuration options and will help you customize your testing experience to meet your needs.
"""

user_prompt_unity = """
Here is the C code:
{code}
"""

unity_prompt_template = ChatPromptTemplate([
    ("system", system_prompt_unity + system_prompt_unity_retrieve),
    ("user", user_prompt_unity),
])

embeddings = DashScopeEmbeddings(
    model="text-embedding-v2",
    dashscope_api_key=os.getenv("OPENAI_API_KEY"),
)

vector_store = Chroma(
    collection_name="unity_documents",
    embedding_function=embeddings,
    persist_directory=PROJECT_PATH + '\\Pre_build\\chroma_langchain_db',  # Where to save data locally, remove if not necessary
)

#########################################
# directory = PROJECT_PATH + "\\Pre_build\\unity_documents"
# files = []
# for filename in os.listdir(directory):
#     if filename.endswith(".md"):
#         files.append(os.path.join(directory, filename))
#
# for file in files:
#     Logger.info(f"Processing file: {file}")
#     loader = TextLoader(file, encoding = 'UTF-8')
#     docs = loader.load()
#     text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
#     all_splits = text_splitter.split_documents(docs)
#     _ = vector_store.add_documents(documents=all_splits)
# Logger.info("All documents have been added to the vector store.")
########################################

retriever = vector_store.as_retriever()
retriever_tool = create_retriever_tool(
    retriever,
    "retrieve_unity_document",
    "Search the unity document and return information about how to use Unity.",
)

tools = [retriever_tool]

# Step 1: Generate an AIMessage that may include a tool-call to be sent.
def query_or_respond(state: MessagesState, writer: StreamWriter):
    """Generate tool call for retrieval or respond."""
    writer({"custom_key": "正在进行知识增强..."})
    llm = get_llm_use_tool_stream()
    llm_with_tools = llm.bind_tools(tools)
    response = llm_with_tools.invoke(unity_prompt_template.format_prompt(code=state["messages"][-1].content))
    # MessagesState appends messages to state instead of overwriting
    return {"messages": [response]}


# Step 2: Execute the retrieval.
tool_node = ToolNode(tools)


# Step 3: Generate a response using the retrieved content.
def generate(state: MessagesState, writer: StreamWriter):
    """Generate answer."""
    # Get generated ToolMessages
    writer({"custom_key": "增强完成，正在进行测试样例生成..."})
    llm = get_llm_stream()
    recent_tool_messages = []
    for message in reversed(state["messages"]):
        if message.type == "tool":
            recent_tool_messages.append(message)
        else:
            break
    tool_messages = recent_tool_messages[::-1]

    # Format into prompt
    docs_content = "\n\n".join(doc.content for doc in tool_messages)
    # print("docs_content:", docs_content)
    system_message_content = (
        system_prompt_unity+
        "\n\n"
        "docs below can help you.\n\n"
        f"{docs_content}"
    )
    conversation_messages = [
        message
        for message in state["messages"]
        if message.type in ("human", "system")
        or (message.type == "ai" and not message.tool_calls)
    ]
    prompt = [SystemMessage(system_message_content)] + conversation_messages

    # Run
    response = llm.invoke(prompt)
    return {"messages": [response]}

def create_subflow():
    """创建子流程"""
    graph_builder = StateGraph(MessagesState)
    graph_builder.add_node("query_or_respond", query_or_respond)
    graph_builder.add_node("tool_node", tool_node)
    graph_builder.add_node("generate", generate)

    graph_builder.set_entry_point("query_or_respond")
    graph_builder.add_conditional_edges(
        "query_or_respond",
        tools_condition,
        {END: END, "tools": "tool_node"},
    )
    graph_builder.add_edge("tool_node", "generate")
    graph_builder.add_edge("generate", END)

    return graph_builder.compile()

if __name__ == "__main__":
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
    subflow = create_subflow()
    # for step in subflow.stream(
    #         {"messages": [{"role": "user", "content": input}]},
    #         stream_mode="values",
    # ):
    #     print(step["messages"][-1])
    response = subflow.invoke(
        {"messages": [{"role": "user", "content": input}]},
    )
    print(response["messages"][-1].content)
    # print(PROJECT_PATH)