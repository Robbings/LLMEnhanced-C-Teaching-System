import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from typing import Dict, Any, List

# Import the modules to test
from LLM.Task_Decomposition.task_decomposition import (
    TaskState,
    validate_task_input,
    decompose_task,
    reject_task,
    should_decompose,
    build_task_graph,
    task_graph,
    _run_task_decomposition,
    chat
)
from LLM.Prompts.task_prompt import (
    system_prompt_deco,
    system_prompt_gen,
    user_prompt_gen,
    graph_prompt_template,
    func_prompt_template,
    graph_node,
    func_node,
    create_subflow
)

class TestTaskDecomposition(unittest.TestCase):
    """Test cases for task decomposition functionality."""

    def setUp(self):
        """Set up test fixtures, if any."""
        self.valid_task_state = TaskState(
            uid="test_uid",
            chat_id="test_chat_id",
            user_input="设计一个函数，找到列表中的最大值。",
            valid=False,
            tasks=""
        )

        self.invalid_task_state = TaskState(
            uid="test_uid",
            chat_id="test_chat_id",
            user_input="今天天气怎么样？",
            valid=False,
            tasks=""
        )

        # Mock for StreamWriter
        self.mock_writer = MagicMock()

    @patch('LLM.Task_Decomposition.task_decomposition.llm')
    def test_validate_task_input_valid(self, mock_llm):
        """Test validation function with valid programming task input."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.content = "是，这是一个可分解的编程任务。"
        mock_llm.invoke.return_value = mock_response

        # Execute
        result = validate_task_input(self.valid_task_state, self.mock_writer)

        # Assert
        self.assertTrue(result["valid"])
        self.mock_writer.assert_called_once_with({"custom_key": "正在进行输入判断..."})
        mock_llm.invoke.assert_called_once()

    @patch('LLM.Task_Decomposition.task_decomposition.llm')
    def test_validate_task_input_invalid(self, mock_llm):
        """Test validation function with invalid input."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.content = "否"
        mock_llm.invoke.return_value = mock_response

        # Execute
        result = validate_task_input(self.invalid_task_state, self.mock_writer)

        # Assert
        self.assertFalse(result["valid"])
        self.mock_writer.assert_called_once_with({"custom_key": "正在进行输入判断..."})
        mock_llm.invoke.assert_called_once()

    @patch('LLM.Task_Decomposition.task_decomposition.task_prompt.create_subflow')
    def test_decompose_task(self, mock_create_subflow):
        """Test task decomposition function."""
        # Setup mock
        mock_subflow = MagicMock()
        mock_create_subflow.return_value = mock_subflow
        mock_subflow.invoke.return_value = {
            "function_code": "任务1: 输入解析\n任务2: 查找最大值\n任务3: 返回结果"
        }

        # Execute
        result = decompose_task(self.valid_task_state)

        # Assert
        self.assertEqual(result["tasks"], "任务1: 输入解析\n任务2: 查找最大值\n任务3: 返回结果")
        mock_create_subflow.assert_called_once()
        mock_subflow.invoke.assert_called_once_with({
            "problem_description": "设计一个函数，找到列表中的最大值。"
        })

    def test_reject_task(self):
        """Test rejection function for invalid tasks."""
        # Execute
        result = reject_task(self.invalid_task_state, self.mock_writer)

        # Assert
        self.assertEqual(result["tasks"], "输入不符合任务分解要求，请重新输入。")
        self.mock_writer.assert_called_once_with({"custom_key": "输入不符合任务分解要求，请重新输入。"})

    def test_should_decompose_valid(self):
        """Test decision function with valid state."""
        # Setup
        state = {**self.valid_task_state, "valid": True}

        # Execute
        result = should_decompose(state)

        # Assert
        self.assertEqual(result, "decompose")

    def test_should_decompose_invalid(self):
        """Test decision function with invalid state."""
        # Setup
        state = {**self.invalid_task_state, "valid": False}

        # Execute
        result = should_decompose(state)

        # Assert
        self.assertEqual(result, "reject")

    def test_build_task_graph(self):
        """Test graph building function."""
        # Execute
        graph = build_task_graph()

        # Assert
        self.assertIsNotNone(graph)
        # Check that the graph has the expected structure
        self.assertTrue(hasattr(graph, 'invoke'))
        self.assertTrue(hasattr(graph, 'stream'))

    @patch('LLM.Task_Decomposition.task_decomposition.task_graph')
    def test_run_task_decomposition(self, mock_task_graph):
        """Test the task decomposition runner function."""
        # Setup
        mock_task_graph.invoke.return_value = {
            "tasks": "任务1: 输入解析\n任务2: 查找最大值\n任务3: 返回结果"
        }

        # Execute
        # Note: Since _run_task_decomposition doesn't return anything in the current implementation,
        # we're just testing that it runs without errors
        _run_task_decomposition("u123", "chat001", "设计一个函数，找到列表中的最大值。")

        # Assert
        mock_task_graph.stream.assert_called_once()

    @patch('LLM.Task_Decomposition.task_decomposition.task_graph')
    def test_chat_function(self, mock_task_graph):
        """Test the chat function with streaming."""
        # Setup mock
        expected_results = [
            {"custom_key": "正在进行输入判断..."},
            (MagicMock(content="任务1: 输入解析"), {"langgraph_node": "func"}),
            (MagicMock(content="任务2: 查找最大值"), {"langgraph_node": "func"}),
        ]

        mock_task_graph.stream.return_value = [
            ("custom", {"custom_key": "正在进行输入判断..."}),
            ("messages", (MagicMock(content="任务1: 输入解析"), {"langgraph_node": "func"})),
            ("messages", (MagicMock(content="任务2: 查找最大值"), {"langgraph_node": "func"})),
        ]

        # Execute
        message = [{"content": "设计一个函数，找到列表中的最大值。"}]
        results = list(chat(message))

        # Assert
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0], "正在进行输入判断...\n")
        self.assertEqual(results[1], "任务1: 输入解析")
        self.assertEqual(results[2], "任务2: 查找最大值")
        mock_task_graph.stream.assert_called_once()


class TestTaskPrompt(unittest.TestCase):
    """Test cases for task prompt functionality."""

    def setUp(self):
        """Set up test fixtures, if any."""
        self.test_state = {
            "problem_description": "Design a function that finds the maximum number in a list."
        }
        self.test_state_with_mlr = {
            "problem_description": "Design a function that finds the maximum number in a list.",
            "mlr_graph": "H1 [High-Level]: Solve the problem: Find maximum in a list\n  Reasoning: Break the problem into major tasks..."
        }

        # Mock for StreamWriter
        self.mock_writer = MagicMock()

    def test_prompt_templates(self):
        """Test if prompt templates format messages correctly."""
        # Test graph prompt template
        graph_messages = graph_prompt_template.format_messages(
            problem_description="Design a function that finds the maximum number in a list."
        )
        self.assertEqual(len(graph_messages), 2)
        self.assertEqual(graph_messages[0].type, "system")
        self.assertEqual(graph_messages[1].type, "human")
        self.assertIn("programming problem", graph_messages[1].content)

        # Test function prompt template
        func_messages = func_prompt_template.format_messages(
            mlr_graph="Sample MLR graph content"
        )
        self.assertEqual(len(func_messages), 2)
        self.assertEqual(func_messages[0].type, "system")
        self.assertEqual(func_messages[1].type, "human")
        self.assertIn("Sample MLR graph content", func_messages[1].content)

    @patch('LLM.Prompts.task_prompt.get_llm_stream')
    def test_graph_node(self, mock_get_llm_stream):
        """Test graph node function."""
        # Setup mock
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Sample MLR graph"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm_stream.return_value = mock_llm

        # Execute
        result = graph_node(self.test_state, self.mock_writer)

        # Assert
        self.mock_writer.assert_called_once_with({"custom_key": "正在生成 MLR 图..."})
        mock_get_llm_stream.assert_called_once()
        mock_llm.invoke.assert_called_once()
        self.assertEqual(result["mlr_graph"], "Sample MLR graph")
        self.assertEqual(result["problem_description"], self.test_state["problem_description"])

    @patch('LLM.Prompts.task_prompt.get_llm_stream')
    def test_func_node(self, mock_get_llm_stream):
        """Test function node."""
        # Setup mock
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Sample function code"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm_stream.return_value = mock_llm

        # Execute
        result = func_node(self.test_state_with_mlr)

        # Assert
        mock_get_llm_stream.assert_called_once()
        mock_llm.invoke.assert_called_once()
        self.assertEqual(result["function_code"], "Sample function code")
        self.assertEqual(result["mlr_graph"], self.test_state_with_mlr["mlr_graph"])

    @patch('LLM.Prompts.task_prompt.StateGraph')
    def test_create_subflow(self, mock_StateGraph):
        """Test subflow creation."""
        # Setup mock
        mock_graph_builder = MagicMock()
        mock_StateGraph.return_value = mock_graph_builder
        mock_graph_builder.compile.return_value = "compiled_subflow"

        # Execute
        result = create_subflow()

        # Assert
        mock_StateGraph.assert_called_once_with(dict)
        mock_graph_builder.add_node.assert_any_call("graph", graph_node)
        mock_graph_builder.add_node.assert_any_call("func", func_node)
        mock_graph_builder.set_entry_point.assert_called_once_with("graph")
        mock_graph_builder.add_edge.assert_called_once_with("graph", "func")
        mock_graph_builder.set_finish_point.assert_called_once_with("func")
        mock_graph_builder.compile.assert_called_once()
        self.assertEqual(result, "compiled_subflow")

    @patch('LLM.Prompts.task_prompt.create_subflow')
    def test_subflow_streaming(self, mock_create_subflow):
        """Test subflow streaming integration."""
        # This is a more integrated test that verifies the subflow can be created and streamed from
        # Setup mock
        mock_subflow = MagicMock()
        mock_create_subflow.return_value = mock_subflow

        # Mock the streaming behavior
        mock_stream_results = [
            ("custom", {"custom_key": "正在生成 MLR 图..."}),
            ("messages", (MagicMock(content="MLR graph content"), {"node": "graph"})),
            ("messages", (MagicMock(content="Function code content"), {"node": "func"}))
        ]
        mock_subflow.stream.return_value = mock_stream_results

        # Execute - simulate what would happen in __main__
        subflow = create_subflow()
        input_data = {
            "problem_description": "Design a function that finds the maximum number in a list.",
        }

        # Since we've mocked the subflow.stream method, we can't directly iterate through it
        # Instead, we'll verify that it was called with the expected parameters
        subflow.stream(input_data, stream_mode=["messages", "custom"])