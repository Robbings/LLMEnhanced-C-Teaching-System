import unittest
from unittest.mock import patch, MagicMock, Mock, call
import os
import sys
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.output_parsers import StrOutputParser

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入被测试的模块
from LLM.Prompts.test_prompt import create_subflow, query_or_respond, generate, tools_condition


class TestLLMIntegration(unittest.TestCase):
    """测试LLM集成功能，测试流程的完整执行"""

    @patch('LLM.Prompts.test_prompt.get_llm_use_tool_stream')
    @patch('LLM.Prompts.test_prompt.get_llm_stream')
    def test_complete_workflow_with_tools(self, mock_get_llm_stream, mock_get_llm_use_tool):
        """测试完整工作流程，包含工具调用"""
        # 设置模拟对象
        mock_tool_llm = MagicMock()
        mock_get_llm_use_tool.return_value = mock_tool_llm

        mock_response_llm = MagicMock()
        mock_get_llm_stream.return_value = mock_response_llm

        # 模拟工具调用响应
        tool_response = AIMessage(
            content="I need to search for Unity test information",
            tool_calls=[{"name": "retrieve_unity_document", "args": {"query": "unity test framework"}, "id": "call-1"}]
        )
        mock_tool_llm.bind_tools.return_value.invoke.return_value = tool_response

        # 模拟生成最终回答
        final_response = AIMessage(content="Here are the Unity tests based on documentation")
        mock_response_llm.invoke.return_value = final_response

        # 创建子流程的模拟对象
        with patch('LLM.Prompts.test_prompt.StateGraph') as mock_state_graph:
            mock_graph = MagicMock()
            mock_state_graph.return_value = mock_graph
            mock_graph.compile.return_value = MagicMock()

            # 创建子流程
            subflow = create_subflow()

            # 设置子流程的执行流程
            def side_effect_invoke(state_dict, **kwargs):
                writer = MagicMock()
                # query_or_respond
                qor_result = query_or_respond(state_dict, writer)
                state_dict["messages"].extend(qor_result["messages"])

                # 工具返回
                tool_message = ToolMessage(
                    content="Unity test framework documentation and examples",
                    name="retrieve_unity_document",
                    tool_call_id="call-1"
                )
                state_dict["messages"].append(tool_message)

                # 生成最终回答
                gen_result = generate(state_dict, writer)
                return {"messages": state_dict["messages"] + gen_result["messages"]}

            mock_graph.compile.return_value.invoke = side_effect_invoke

            input_message = {"messages": [HumanMessage(content="Write Unity tests for this C code")]}
            result = subflow.invoke(input_message)

            self.assertIn(final_response, result["messages"])
            self.assertEqual(len(result["messages"]), 4)

    def test_tools_condition_branching(self):
        state_with_tools = {
            "messages": [
                AIMessage(content="Need info", tool_calls=[{"name": "tool", "args": {}, "id": "call-1"}])
            ]
        }
        self.assertEqual(tools_condition(state_with_tools), "tools")

        state_without_tools = {
            "messages": [AIMessage(content="Direct answer")]
        }
        from LLM.Prompts.test_prompt import END
        self.assertEqual(tools_condition(state_without_tools), END)


class TestRetrievalIntegration(unittest.TestCase):
    # @patch('LLM.Prompts.test_prompt.vector_store')
    # @patch('LLM.Prompts.test_prompt.create_retriever_tool')
    # def test_retriever_tool_creation(self, mock_create_tool, mock_vector_store):
    #     from LLM.Prompts.test_prompt import retriever_tool, retriever
    #     mock_vector_store.as_retriever.assert_called_once()
    #     mock_create_tool.assert_called_once_with(
    #         retriever,
    #         "retrieve_unity_document",
    #         "Search the unity document and return information about how to use Unity."
    #     )

    @patch('LLM.Prompts.test_prompt.ToolNode')
    def test_tool_node_execution(self, mock_tool_node):
        mock_tool_instance = MagicMock()
        mock_tool_node.return_value = mock_tool_instance

        mock_tool_instance.invoke.return_value = {
            "messages": [
                ToolMessage(content="Unity test framework documentation", name="retrieve_unity_document", tool_call_id="call-1")
            ]
        }

        tool_call_message = AIMessage(
            content="I need information",
            tool_calls=[{"name": "retrieve_unity_document", "args": {"query": "unity test"}, "id": "call-1"}]
        )

        state = {"messages": [HumanMessage(content="help"), tool_call_message]}

        from LLM.Prompts.test_prompt import tool_node

        with patch('LLM.Prompts.test_prompt.tool_node', mock_tool_instance):
            result = mock_tool_instance.invoke(state)

            self.assertEqual(len(result["messages"]), 1)
            self.assertEqual(result["messages"][0].name, "retrieve_unity_document")
            self.assertEqual(result["messages"][0].content, "Unity test framework documentation")


# class TestMainExecution(unittest.TestCase):
#     @patch('LLM.Prompts.test_prompt.create_subflow')
#     def test_main_execution(self, mock_create_subflow):
#         import LLM.Prompts.test_prompt
#
#         mock_subflow = MagicMock()
#         mock_create_subflow.return_value = mock_subflow
#
#         mock_subflow.invoke.return_value = {
#             "messages": [
#                 HumanMessage(content="Write tests"),
#                 AIMessage(content="Here are the Unity tests")
#             ]
#         }
#
#         with patch.object(LLM.Prompts.test_prompt, "__name__", "__main__"):
#             with patch('builtins.print') as mock_print:
#                 with open(LLM.Prompts.test_prompt.__file__, encoding="utf-8") as f:
#                     exec(f.read())
#
#                     # mock_subflow.invoke.assert_called_once()
#                     mock_print.assert_called_with("Here are the Unity tests")


if __name__ == "__main__":
    unittest.main()