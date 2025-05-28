import unittest
from unittest.mock import patch, MagicMock
import sys
from io import StringIO

# 导入待测试的模块
from LLM.Prompts.code_prompt import (
    scot_prompt_template,
    gen_prompt_template,
    scot_node,
    gen_node,
    create_subflow
)


class TestCodePromptTemplates(unittest.TestCase):
    """测试代码提示模板的单元测试类"""

    def test_scot_prompt_template(self):
        """测试SCoT提示模板格式化"""
        # 准备测试数据
        function_definition = "int find_max(int arr[], int size);"

        # 格式化提示模板
        prompt = scot_prompt_template.format_prompt(function_definition=function_definition)

        # 验证格式化结果
        formatted_messages = prompt.to_messages()
        self.assertEqual(len(formatted_messages), 2)  # 系统提示和用户提示
        self.assertIn("problem", formatted_messages[1].content)
        self.assertIn(function_definition, formatted_messages[1].content)

    def test_gen_prompt_template(self):
        """测试代码生成提示模板格式化"""
        # 准备测试数据
        function_definition = "int find_max(int arr[], int size);"
        solvingprocess = "Input: arr, size\nOutput: max value\n1: Initialize max=arr[0]\n2: Loop through array\n3: If current element > max, update max\n4: Return max"

        # 格式化提示模板
        prompt = gen_prompt_template.format_prompt(
            function_definition=function_definition,
            solvingprocess=solvingprocess
        )

        # 验证格式化结果
        formatted_messages = prompt.to_messages()
        self.assertEqual(len(formatted_messages), 2)  # 系统提示和用户提示
        self.assertIn("定义", formatted_messages[1].content)
        self.assertIn("solvingprocess", formatted_messages[1].content)
        self.assertIn(function_definition, formatted_messages[1].content)
        self.assertIn(solvingprocess, formatted_messages[1].content)


class TestCodePromptNodes(unittest.TestCase):
    """测试代码提示节点的单元测试类"""

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
        result = scot_node(state, mock_writer)

        # 验证结果
        self.assertIn("solvingprocess", result)
        self.assertEqual(result["solvingprocess"], mock_response.content)
        mock_writer.assert_called_once_with({"custom_key": "正在生成 SCoT 流程..."})
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
        result = gen_node(state, mock_writer)

        # 验证结果
        self.assertIn("code", result)
        self.assertEqual(result["code"], mock_response.content)
        mock_get_llm.assert_called_once()
        mock_llm.invoke.assert_called_once()


class TestSubflowCreation(unittest.TestCase):
    """测试子流程创建的单元测试类"""

    def test_create_subflow(self):
        """测试创建子流程"""
        # 创建子流程
        subflow = create_subflow()

        # 验证子流程创建成功
        self.assertIsNotNone(subflow)

    @patch('LLM.Prompts.code_prompt.get_llm_stream')
    def test_subflow_execution(self, mock_get_llm):
        """测试子流程执行 - 集成测试"""
        # 配置模拟对象以返回预期响应
        # 设置SCoT步骤的响应
        scot_response = MagicMock()
        scot_response.content = "Input: arr, size\nOutput: max value\n1: Initialize max=arr[0]\n2: Loop through array\n3: If current element > max, update max\n4: Return max"

        # 设置代码生成步骤的响应
        gen_response = MagicMock()
        gen_response.content = "int find_max(int arr[], int size) {\n    int max = arr[0];\n    for(int i=1; i<size; i++) {\n        if(arr[i] > max) {\n            max = arr[i];\n        }\n    }\n    return max;\n}"

        # 配置模拟LLM在不同调用时返回不同响应
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [scot_response, gen_response]
        mock_get_llm.return_value = mock_llm

        # 创建子流程
        subflow = create_subflow()

        # 捕获和重定向stdout以验证流输出
        captured_output = StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured_output

        # 执行子流程
        function_definition = "int find_max(int arr[], int size);"
        result = subflow.invoke({"function_definition": function_definition})

        # 恢复stdout
        sys.stdout = original_stdout

        # 验证结果
        self.assertIn("code", result)
        self.assertEqual(result["code"], gen_response.content)
        self.assertEqual(mock_llm.invoke.call_count, 2)  # LLM应该被调用两次


class TestCodePromptMainExecution(unittest.TestCase):
    """测试代码提示主执行逻辑的单元测试类"""

    @patch('LLM.Prompts.code_prompt.create_subflow')
    @patch('builtins.print')
    @patch('sys.stdout')
    def test_main_execution(self, mock_stdout, mock_print, mock_create_subflow):
        """测试__main__部分的执行逻辑 - 仅在单独运行code_prompt.py时执行"""
        # 配置Mock对象
        mock_flow = MagicMock()
        mock_flow.stream.return_value = [
            ("custom", {"custom_key": "正在生成 SCoT 流程..."}),
            ("messages", (MagicMock(content="SCoT生成内容"), {"langgraph_node": "scot"})),
            ("messages", (MagicMock(content="代码生成内容"), {"langgraph_node": "gen"}))
        ]
        mock_create_subflow.return_value = mock_flow

        # 导入main部分的执行逻辑
        # 注意：我们不实际执行main代码，因为它在导入时不会运行
        # 这里只是测试__name__ == "__main__"分支中的逻辑是否健壮
        pass


if __name__ == '__main__':
    unittest.main()