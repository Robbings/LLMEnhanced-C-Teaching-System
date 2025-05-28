import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

# 添加项目根目录到路径以便导入模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LLM.Prompts.question_report import (
    question_report_node,
    question_report_prompt_template,
    report_template,
    system_prompt_question_report,
    user_prompt_question_report
)


class TestQuestionReport(unittest.TestCase):
    """测试代码分析报告生成功能"""

    def setUp(self):
        """设置测试所需的通用变量"""
        self.test_question = "实现一个冒泡排序算法"
        self.test_code = """
        def bubble_sort(arr):
            n = len(arr)
            for i in range(n):
                for j in range(0, n - i - 1):
                    if arr[j] > arr[j + 1]:
                        arr[j], arr[j + 1] = arr[j + 1], arr[j]
            return arr
        """
        self.test_state = {
            "question": self.test_question,
            "code": self.test_code
        }

        # 模拟的报告内容
        self.mock_report_content = "# 🧾 代码分析报告\n\n## 📌 一、功能实现概述\n\n- **输出正确性**：代码正确实现了冒泡排序算法"

    def test_report_template_structure(self):
        """测试报告模板是否符合预期结构"""
        self.assertIn("# 🧾 代码分析报告", report_template)
        self.assertIn("## 📌 一、功能实现概述", report_template)
        self.assertIn("## 🧠 二、代码结构分析", report_template)
        self.assertIn("## 🛠 三、算法与逻辑分析", report_template)
        self.assertIn("## 🧪 四、错误与改进建议", report_template)
        self.assertIn("## 📊 五、评分与等级", report_template)
        self.assertIn("## 📢 六、综合评语", report_template)

    def test_prompt_templates_content(self):
        """测试各个提示模板的内容是否正确"""
        self.assertIn("你是一个智能教学辅助系统", system_prompt_question_report)
        self.assertIn("请根据以下题目描述和学生代码", user_prompt_question_report)

        # 测试提示模板组合
        formatted_prompt = question_report_prompt_template.format_prompt(
            question=self.test_question,
            code=self.test_code
        )
        prompt_text = formatted_prompt.to_string()

        # 验证问题和代码是否正确嵌入到模板中
        self.assertIn(self.test_question, prompt_text)
        self.assertIn(self.test_code, prompt_text)

    @patch('LLM.Prompts.question_report.get_llm_stream')
    def test_question_report_node_success(self, mock_get_llm):
        """测试question_report_node函数是否正确处理并返回结果"""
        # 设置模拟LLM的返回值
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = self.mock_report_content
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        # 调用被测函数
        result = question_report_node(self.test_state)

        # 验证结果
        self.assertEqual(result["question"], self.test_question)
        self.assertEqual(result["code"], self.test_code)
        self.assertEqual(result["report"], self.mock_report_content)

        # 验证LLM是否被正确调用
        mock_get_llm.assert_called_once()
        mock_llm.invoke.assert_called_once()

    @patch('LLM.Prompts.question_report.get_llm_stream')
    def test_question_report_node_empty_inputs(self, mock_get_llm):
        """测试对空输入的处理"""
        # 设置模拟LLM的返回值
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Error: Empty input"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        # 调用被测函数，使用空输入
        empty_state = {"question": "", "code": ""}
        result = question_report_node(empty_state)

        # 验证结果
        self.assertEqual(result["question"], "")
        self.assertEqual(result["code"], "")
        self.assertEqual(result["report"], "Error: Empty input")

    @patch('LLM.Prompts.question_report.get_llm_stream')
    def test_question_report_node_exception_handling(self, mock_get_llm):
        """测试异常处理"""
        # 设置模拟LLM抛出异常
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("LLM Error")
        mock_get_llm.return_value = mock_llm

        # 调用被测函数并验证是否抛出异常
        with self.assertRaises(Exception):
            question_report_node(self.test_state)

    def test_prompt_formatting(self):
        """测试提示格式化逻辑"""
        # 测试各种边界情况的代码和问题描述
        test_cases = [
            {"question": "测试问题1", "code": "def test(): pass"},
            {"question": "", "code": "def test(): pass"},
            {"question": "测试问题3", "code": ""},
            {"question": "测试问题\n包含\n换行符", "code": "def test():\n    pass"},
            {"question": "测试问题包含特殊字符!@#$%^&*()", "code": "def test(): # 注释\n    pass"}
        ]

        for case in test_cases:
            formatted_prompt = question_report_prompt_template.format_prompt(
                question=case["question"],
                code=case["code"]
            )
            prompt_text = formatted_prompt.to_string()

            # 验证问题和代码是否正确嵌入到模板中
            self.assertIn(case["question"], prompt_text)
            self.assertIn(case["code"], prompt_text)


if __name__ == '__main__':
    unittest.main()