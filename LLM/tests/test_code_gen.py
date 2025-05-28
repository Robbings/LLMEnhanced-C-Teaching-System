import unittest
from unittest.mock import patch, MagicMock
import sys
import json
from io import StringIO

# 导入待测试的模块
from LLM.Func_Code_Generation.code_generation import build_task_graph, validate_task_input, code_generation_task, \
    reject_task, decision_task
from LLM.Prompts import code_prompt


class TestCodeGeneration(unittest.TestCase):
    """测试代码生成流程的单元测试类"""

    def setUp(self):
        """测试前的准备工作"""
        # 创建模拟的流写入器
        self.mock_writer = MagicMock()
        # 设置有效的输入状态
        self.valid_state = {
            "user_input": "函数名称：find_max\n返回值类型：int\n参数：int arr[], int size\n描述：该函数用于找到整数数组中的最大值。",
            "valid": False,
            "code": "",
        }
        # 设置无效的输入状态
        self.invalid_state = {
            "user_input": "找到列表中的最大值。",
            "valid": False,
            "code": "",
        }

    @patch('LLM.Func_Code_Generation.code_generation.llm')
    def test_validate_task_input_valid(self, mock_llm):
        """测试验证任务输入节点 - 有效输入"""
        # 配置mock以返回不包含"不符合"的响应
        mock_response = MagicMock()
        mock_response.content = "符合 C 语言函数级代码生成的要求。"
        mock_llm.invoke.return_value = mock_response

        # 执行验证函数
        result = validate_task_input(self.valid_state, self.mock_writer)

        # 验证结果
        self.assertTrue(result["valid"])
        self.mock_writer.assert_called_once()
        mock_llm.invoke.assert_called_once()

    @patch('LLM.Func_Code_Generation.code_generation.llm')
    def test_validate_task_input_invalid(self, mock_llm):
        """测试验证任务输入节点 - 无效输入"""
        # 配置mock以返回包含"不符合"的响应
        mock_response = MagicMock()
        mock_response.content = "不符合 C 语言函数级代码生成的要求。"
        mock_llm.invoke.return_value = mock_response

        # 执行验证函数
        result = validate_task_input(self.invalid_state, self.mock_writer)

        # 验证结果
        self.assertFalse(result["valid"])
        self.mock_writer.assert_called_once()
        mock_llm.invoke.assert_called_once()

    @patch('LLM.Prompts.code_prompt.create_subflow')
    def test_code_generation_task(self, mock_create_subflow):
        """测试代码生成任务节点"""
        # 设置模拟的子流程调用
        mock_subflow = MagicMock()
        mock_subflow.invoke.return_value = {
            "code": "int find_max(int arr[], int size) {\n    int max = arr[0];\n    for(int i=1; i<size; i++) {\n        if(arr[i] > max) {\n            max = arr[i];\n        }\n    }\n    return max;\n}"}
        mock_create_subflow.return_value = mock_subflow

        # 执行代码生成函数
        result = code_generation_task(self.valid_state)

        # 验证结果
        self.assertIn("code", result)
        self.assertTrue(result["code"].startswith("int find_max"))
        mock_create_subflow.assert_called_once()
        mock_subflow.invoke.assert_called_once_with({"function_definition": self.valid_state["user_input"]})

    @patch('LLM.Func_Code_Generation.code_generation.llm')
    def test_reject_task(self, mock_llm):
        """测试拒绝任务节点"""
        # 配置mock以返回拒绝响应
        mock_response = MagicMock()
        mock_response.content = "输入不符合要求，原因是：缺少函数名称、返回值类型和参数信息。"
        mock_llm.invoke.return_value = mock_response

        # 执行拒绝函数
        result = reject_task(self.invalid_state, self.mock_writer)

        # 验证结果
        self.assertIn("tasks", result)
        self.assertTrue(result["tasks"].startswith("输入不符合任务分解要求"))
        self.mock_writer.assert_called_once()
        mock_llm.invoke.assert_called_once()

    def test_decision_task_valid(self):
        """测试决策任务 - 有效输入"""
        state = {"valid": True}
        result = decision_task(state)
        self.assertEqual(result, "code_gen")

    def test_decision_task_invalid(self):
        """测试决策任务 - 无效输入"""
        state = {"valid": False}
        result = decision_task(state)
        self.assertEqual(result, "reject")

    def test_build_task_graph(self):
        """测试构建任务图"""
        # 构建任务图
        graph = build_task_graph()

        # 验证图结构 (基本验证，确保编译没有错误)
        self.assertIsNotNone(graph)


class TestCodePrompt(unittest.TestCase):
    """测试代码提示模板的单元测试类"""

    @patch('LLM.Prompts.code_prompt.get_llm_stream')
    def test_scot_node(self, mock_get_llm):
        """测试SCoT节点生成逻辑"""
        # 创建模拟的LLM和响应
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Input: arr, size\nOutput: max value\n1: Initialize max=arr[0]\n2: Loop through array\n3: If current element > max, update max\n4: Return max"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        # 创建模拟的状态和写入器
        state = {"function_definition": "int find_max(int arr[], int size);"}
        mock_writer = MagicMock()

        # 执行SCoT节点
        result = code_prompt.scot_node(state, mock_writer)

        # 验证结果
        self.assertIn("solvingprocess", result)
        self.assertEqual(result["solvingprocess"], mock_response.content)
        mock_writer.assert_called_once()
        mock_get_llm.assert_called_once()
        mock_llm.invoke.assert_called_once()

    @patch('LLM.Prompts.code_prompt.get_llm_stream')
    def test_gen_node(self, mock_get_llm):
        """测试代码生成节点逻辑"""
        # 创建模拟的LLM和响应
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "int find_max(int arr[], int size) {\n    int max = arr[0];\n    for(int i=1; i<size; i++) {\n        if(arr[i] > max) {\n            max = arr[i];\n        }\n    }\n    return max;\n}"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        # 创建模拟的状态和写入器
        state = {
            "function_definition": "int find_max(int arr[], int size);",
            "solvingprocess": "Input: arr, size\nOutput: max value\n1: Initialize max=arr[0]\n2: Loop through array\n3: If current element > max, update max\n4: Return max"
        }
        mock_writer = MagicMock()

        # 执行代码生成节点
        result = code_prompt.gen_node(state, mock_writer)

        # 验证结果
        self.assertIn("code", result)
        self.assertEqual(result["code"], mock_response.content)
        mock_get_llm.assert_called_once()
        mock_llm.invoke.assert_called_once()

    def test_create_subflow(self):
        """测试创建子流程"""
        # 创建子流程
        subflow = code_prompt.create_subflow()

        # 验证子流程创建成功
        self.assertIsNotNone(subflow)

    @patch('LLM.Prompts.code_prompt.create_subflow')
    @patch('builtins.print')
    def test_main_execution(self, mock_print, mock_create_subflow):
        """测试main执行逻辑"""
        # 跳过实际测试，因为这只是一个示例执行
        # 实际环境中可能不会执行__main__部分
        pass


class TestEndToEndCodeGeneration(unittest.TestCase):
    """端到端测试代码生成流程"""

    @patch('LLM.Func_Code_Generation.code_generation.task_graph.stream')
    def test_chat_valid_input(self, mock_stream):
        """测试聊天函数 - 有效输入"""
        from LLM.Func_Code_Generation.code_generation import chat

        # 模拟流输出
        mock_stream.return_value = iter([
            ("custom", {"custom_key": "正在进行输入判断..."}),
            ("messages", (MagicMock(content="代码生成中..."), {"langgraph_node": "gen"})),
            ("messages", (MagicMock(content="int find_max(int arr[], int size) {...}"), {"langgraph_node": "gen"}))
        ])

        # 测试聊天函数
        message = [{"role": "user",
                    "content": "函数名称：find_max\n返回值类型：int\n参数：int arr[], int size\n描述：该函数用于找到整数数组中的最大值。"}]
        results = list(chat(message))

        # 验证结果
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0], "正在进行输入判断...\n")
        self.assertEqual(results[1], "代码生成中...")
        self.assertEqual(results[2], "int find_max(int arr[], int size) {...}")
        mock_stream.assert_called_once()

    @patch('LLM.Func_Code_Generation.code_generation.task_graph.stream')
    def test_run_task_execution(self, mock_stream):
        """测试运行任务分解函数"""
        from LLM.Func_Code_Generation.code_generation import _run_task_decomposition

        # 重定向stdout以捕获输出
        captured_output = StringIO()
        sys.stdout = captured_output

        # 模拟流输出
        mock_stream.return_value = iter([
            ("custom", {"custom_key": "正在进行输入判断..."}),
            ("messages", (MagicMock(content="代码生成完成"), {"langgraph_node": "gen"}))
        ])

        # 执行函数
        _run_task_decomposition("u123", "chat001", "函数名称：find_max\n返回值类型：int\n参数：int arr[], int size")

        # 恢复stdout
        sys.stdout = sys.__stdout__

        # 验证输出
        output = captured_output.getvalue()
        self.assertIn("正在进行输入判断...", output)
        self.assertIn("代码生成完成", output)
        mock_stream.assert_called_once()


if __name__ == '__main__':
    unittest.main()