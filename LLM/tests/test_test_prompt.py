import unittest
from unittest.mock import patch, MagicMock, Mock
import os
import sys
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.messages.base import BaseMessage
from langchain_core.prompts import ChatPromptTemplate

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入被测试的模块
from Prompts.test_prompt import (
    unity_prompt_template,
    query_or_respond,
    generate,
    create_subflow,
    tools,
    tools_condition,
    END
)


class TestPromptTemplate(unittest.TestCase):
    """测试prompt模板相关功能"""

    def test_unity_prompt_template(self):
        """测试Unity测试提示模板是否正确构造"""
        test_code = "int add(int a, int b) { return a + b; }"
        formatted_prompt = unity_prompt_template.format_prompt(code=test_code)

        # 验证格式化后的提示内容是否包含测试代码
        self.assertIn(test_code, formatted_prompt.to_string())

        # 验证提示模板中的消息类型和数量
        messages = formatted_prompt.to_messages()
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].type, "system")
        self.assertEqual(messages[1].type, "human")


class TestQueryOrRespondFunction(unittest.TestCase):
    """测试query_or_respond函数功能"""

    @patch('Prompts.test_prompt.get_llm_use_tool_stream')
    def test_query_or_respond_with_tool_call(self, mock_get_llm):
        """测试query_or_respond函数使用工具调用的情况"""
        # 模拟LLM返回带有工具调用的消息
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        # 创建模拟响应，包含工具调用
        mock_ai_message = AIMessage(content="I need to search for information",
                                    tool_calls=[{"name": "retrieve_unity_document", "args": {"query": "unity test"}, "id": "tool_call_1"}])
        mock_llm.bind_tools.return_value.invoke.return_value = mock_ai_message

        # 创建测试状态和写入器
        state = {"messages": [HumanMessage(content="Write unity tests for this code")]}
        writer = MagicMock()

        # 执行函数
        result = query_or_respond(state, writer)

        # 验证结果
        self.assertEqual(len(result["messages"]), 1)
        self.assertEqual(result["messages"][0], mock_ai_message)
        self.assertTrue(mock_llm.bind_tools.called)
        writer.assert_called_with({"custom_key": "正在进行知识增强..."})

    @patch('Prompts.test_prompt.get_llm_use_tool_stream')
    def test_query_or_respond_without_tool_call(self, mock_get_llm):
        """测试query_or_respond函数不使用工具调用的情况"""
        # 模拟LLM返回不带工具调用的消息
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        # 创建模拟响应，不包含工具调用
        mock_ai_message = AIMessage(content="Here's how to write Unity tests")
        mock_llm.bind_tools.return_value.invoke.return_value = mock_ai_message

        # 创建测试状态和写入器
        state = {"messages": [HumanMessage(content="Write unity tests for this code")]}
        writer = MagicMock()

        # 执行函数
        result = query_or_respond(state, writer)

        # 验证结果
        self.assertEqual(len(result["messages"]), 1)
        self.assertEqual(result["messages"][0], mock_ai_message)
        writer.assert_called_with({"custom_key": "正在进行知识增强..."})


class TestGenerateFunction(unittest.TestCase):
    """测试generate函数功能"""

    @patch('Prompts.test_prompt.get_llm_stream')
    def test_generate_with_tool_messages(self, mock_get_llm):
        """测试generate函数处理工具消息的情况"""
        # 模拟LLM
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        # 创建模拟响应
        mock_ai_response = AIMessage(content="Here are the Unity tests based on the retrieved information")
        mock_llm.invoke.return_value = mock_ai_response

        # 创建测试状态，包含工具消息
        state = {
            "messages": [
                SystemMessage(content="System message"),
                HumanMessage(content="Write unity tests"),
                AIMessage(
                    content="I'll search for information",
                    tool_calls=[
                        {"name": "retrieve_unity_document", "args": {}, "id": "tool_call_1"}
                    ]
                ),
                ToolMessage(content="Unity test framework documentation", tool_call_id="tool_call_1"),
                ToolMessage(content="More Unity test examples", tool_call_id="tool_call_1")
            ]
        }
        writer = MagicMock()

        # 执行函数
        result = generate(state, writer)

        # 验证结果
        self.assertEqual(len(result["messages"]), 1)
        self.assertEqual(result["messages"][0], mock_ai_response)
        writer.assert_called_with({"custom_key": "增强完成，正在进行测试样例生成..."})

        # 验证LLM调用时传入的提示包含工具消息内容
        args, kwargs = mock_llm.invoke.call_args
        prompt_messages = args[0]
        system_message = prompt_messages[0]
        self.assertIn("Unity test framework documentation", system_message.content)
        self.assertIn("More Unity test examples", system_message.content)

    @patch('Prompts.test_prompt.get_llm_stream')
    def test_generate_without_tool_messages(self, mock_get_llm):
        """测试generate函数不包含工具消息的情况"""
        # 模拟LLM
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        # 创建模拟响应
        mock_ai_response = AIMessage(content="Here are the Unity tests")
        mock_llm.invoke.return_value = mock_ai_response

        # 创建测试状态，不包含工具消息
        state = {
            "messages": [
                SystemMessage(content="System message"),
                HumanMessage(content="Write unity tests"),
                AIMessage(content="Here's how to write Unity tests")
            ]
        }
        writer = MagicMock()

        # 执行函数
        result = generate(state, writer)

        # 验证结果
        self.assertEqual(len(result["messages"]), 1)
        self.assertEqual(result["messages"][0], mock_ai_response)
        writer.assert_called_with({"custom_key": "增强完成，正在进行测试样例生成..."})


class TestToolsCondition(unittest.TestCase):
    """测试tools_condition函数"""

    def test_tools_condition_with_tool_calls(self):
        """测试带有工具调用的消息条件判断"""
        # 创建测试状态
        state = {
            "messages": [
                AIMessage(content="I need information", tool_calls=[{"name": "retrieve_unity_document", "args": {}, "id": "tool_call_1"}])
            ]
        }

        # 执行条件判断
        result = tools_condition(state)

        # 验证结果
        self.assertEqual(result, "tools")

    def test_tools_condition_without_tool_calls(self):
        """测试不带工具调用的消息条件判断"""
        # 创建测试状态
        state = {
            "messages": [
                AIMessage(content="Here's how to write Unity tests")
            ]
        }

        # 执行条件判断
        result = tools_condition(state)

        # 验证结果
        self.assertEqual(result, END)


class TestCreateSubflow(unittest.TestCase):
    """测试创建子流程功能"""

    @patch('Prompts.test_prompt.StateGraph')
    def test_create_subflow(self, mock_state_graph):
        """测试创建子流程的功能"""
        # 设置模拟对象
        mock_graph_builder = MagicMock()
        mock_state_graph.return_value = mock_graph_builder
        mock_graph_builder.compile.return_value = "compiled_graph"

        # 执行函数
        result = create_subflow()

        # 验证结果
        self.assertEqual(result, "compiled_graph")

        # 验证调用过程
        mock_graph_builder.add_node.assert_any_call("query_or_respond", query_or_respond)
        mock_graph_builder.add_node.assert_any_call("tool_node", unittest.mock.ANY)
        mock_graph_builder.add_node.assert_any_call("generate", generate)

        mock_graph_builder.set_entry_point.assert_called_once_with("query_or_respond")

        mock_graph_builder.add_conditional_edges.assert_called_once()
        mock_graph_builder.add_edge.assert_any_call("tool_node", "generate")
        mock_graph_builder.add_edge.assert_any_call("generate", END)

        mock_graph_builder.compile.assert_called_once()


if __name__ == "__main__":
    unittest.main()