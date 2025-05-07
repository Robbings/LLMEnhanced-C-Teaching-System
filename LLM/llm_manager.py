# llm_manager.py
from langchain_openai import ChatOpenAI
from LLMEnhanced_C_Teaching_System.settings import LLM_MODEL, LLM_MODEL_TOOL

# 模块加载时就实例化一次
llm_stream = ChatOpenAI(model=LLM_MODEL, streaming=True, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
llm_no_stream = ChatOpenAI(model=LLM_MODEL, streaming=False, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
llm_use_tool =ChatOpenAI(model=LLM_MODEL_TOOL, streaming=False, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
llm_use_tool_stream = ChatOpenAI(model=LLM_MODEL_TOOL, streaming=True, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")


def get_llm_stream():
    return llm_stream

def get_llm_no_stream():
    return llm_no_stream

def get_llm_use_tool():
    return llm_use_tool

def get_llm_use_tool_stream():
    return llm_use_tool_stream
