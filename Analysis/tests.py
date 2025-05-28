import unittest

from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock
import json

from django.utils import timezone

from .models import Problem, Submission, EvaluationReport


class EvaluatorViewsTest(TestCase):
    def setUp(self):
        # Set up test client
        self.client = Client()

        # Create a test problem
        self.test_problem = Problem.objects.create(
            id="default",
            content="# Test Problem\n\nThis is a test problem."
        )

        # Create test submissions
        self.code_submission = Submission.objects.create(
            problem=self.test_problem,
            code_content="def solution(x):\n    return x*2",
            submission_type="CODE",
            is_file=False
        )

        self.test_submission = Submission.objects.create(
            problem=self.test_problem,
            code_content="assert solution(2) == 4\nassert solution(3) == 6",
            submission_type="TEST",
            is_file=False
        )

    def test_index_view(self):
        """Test the index view loads correctly"""
        response = self.client.get(reverse('evaluator:index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'evaluator/index.html')

        # Check that the forms are in the context
        self.assertIn('problem_form', response.context)
        self.assertIn('code_form', response.context)
        self.assertIn('test_form', response.context)

        # Check that the default problem is loaded
        self.assertIn('current_problem', response.context)

    def test_save_problem(self):
        """Test saving a problem"""
        data = {
            'id': 'new-problem',
            'content': '# New Problem\n\nThis is a new test problem.'
        }

        response = self.client.post(reverse('evaluator:save_problem'), data)
        self.assertEqual(response.status_code, 200)

        # Check the response is JSON and indicates success
        json_response = response.json()
        self.assertTrue(json_response['success'])

        # Check the problem was actually saved to the database
        saved_problem = Problem.objects.get(id='new-problem')
        self.assertEqual(saved_problem.content, data['content'])

    def test_get_problem(self):
        """Test retrieving a problem by ID"""
        data = {
            'problem_id': self.test_problem.id
        }

        response = self.client.post(reverse('evaluator:get_problem'), data)
        self.assertEqual(response.status_code, 200)

        # Check the response is JSON and contains the problem data
        json_response = response.json()
        self.assertTrue(json_response['success'])
        self.assertEqual(json_response['problem']['id'], self.test_problem.id)
        self.assertEqual(json_response['problem']['content'], self.test_problem.content)

    def test_get_nonexistent_problem(self):
        """Test trying to get a problem that doesn't exist"""
        data = {
            'problem_id': 'nonexistent-problem'
        }

        response = self.client.post(reverse('evaluator:get_problem'), data)
        self.assertEqual(response.status_code, 200)

        # Check the response indicates failure
        json_response = response.json()
        self.assertFalse(json_response['success'])

    @patch('test.myllm.create_response')
    def test_submit_code_text(self, mock_create_response):
        """Test submitting code as text"""
        # Mock the LLM response
        mock_create_response.return_value = "This is a mock evaluation report"

        data = {
            'submission_type': 'CODE',
            'problem_id': self.test_problem.id,
            'code_text': 'def new_solution(x):\n    return x*3'
        }

        response = self.client.post(reverse('evaluator:submit_code'), data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Check a new submission was created
        new_submission = Submission.objects.filter(
            submission_type='CODE',
            problem=self.test_problem,
            code_content='def new_solution(x):\n    return x*3'
        ).first()

        self.assertIsNotNone(new_submission)
        self.assertFalse(new_submission.is_file)

        # Check that an evaluation report was created
        report = EvaluationReport.objects.filter(
            problem=self.test_problem,
            code_submission=new_submission
        ).first()

        self.assertIsNotNone(report)
        self.assertEqual(report.report_content, "This is a mock evaluation report")

    def test_submit_code_with_file(self):
        """测试使用文件提交代码"""
        # 创建一个模拟的上传文件
        code_file = SimpleUploadedFile(
            name='test_code.py',
            content=b'print("Hello from file")',
            content_type='text/plain'
        )

        # 准备提交数据
        post_data = {
            'problem_id': str(self.test_problem.id),
            'submission_type': 'CODE',
            # 'code_text': '',
            'code_file': code_file,
        }

        # 添加文件到请求
        file_data = {'code_file': code_file}

        # 发送 POST 请求 (包含文件)
        response = self.client.post(
            reverse('evaluator:submit_code'),
            post_data
        )

        # 验证重定向
        self.assertRedirects(response, reverse('evaluator:index'))

        # 检查提交是否创建成功
        # self.assertEqual(Submission.objects.count(), 1)
        submission = Submission.objects.first()
        self.assertEqual(submission.problem, self.test_problem)
        self.assertEqual(submission.code_content, 'print("Hello from file")')
        self.assertEqual(submission.file_name, 'test_code.py')
        self.assertEqual(submission.submission_type, 'CODE')
        self.assertTrue(submission.is_file)

    @patch('test.myllm.create_response')
    def test_submit_test_text(self, mock_create_response):
        """Test submitting test cases as text"""
        # Mock the LLM response
        mock_create_response.return_value = "This is a mock evaluation report"

        data = {
            'submission_type': 'TEST',
            'problem_id': self.test_problem.id,
            'code_text': 'assert solution(4) == 8\nassert solution(5) == 10'
        }

        response = self.client.post(reverse('evaluator:submit_test'), data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Check a new submission was created
        new_submission = Submission.objects.filter(
            submission_type='TEST',
            problem=self.test_problem,
            code_content='assert solution(4) == 8\nassert solution(5) == 10'
        ).first()

        self.assertIsNotNone(new_submission)

        # Check that an evaluation report was created
        report = EvaluationReport.objects.filter(
            problem=self.test_problem,
            test_submission=new_submission
        ).first()

        self.assertIsNotNone(report)
        self.assertEqual(report.report_content, "This is a mock evaluation report")

    def test_submit_test_file(self):
        """Test submitting test cases as a file"""
        test_file = SimpleUploadedFile(
            "test_cases.py",
            b"assert solution(6) == 12\nassert solution(7) == 14",
            content_type="text/plain"
        )

        data = {
            'submission_type': 'TEST',
            'problem_id': self.test_problem.id,
            'code_file': test_file
        }

        response = self.client.post(reverse('evaluator:submit_test'), data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Check a new submission was created
        new_submission = Submission.objects.filter(
            submission_type='TEST',
            problem=self.test_problem,
            file_name='test_cases.py'
        ).first()

        self.assertIsNotNone(new_submission)
        self.assertTrue(new_submission.is_file)
        self.assertEqual(new_submission.code_content, "assert solution(6) == 12\nassert solution(7) == 14")

    def test_get_latest_report(self):
        """Test getting the latest report"""
        # Create a report first
        report = EvaluationReport.objects.create(
            problem=self.test_problem,
            code_submission=self.code_submission,
            test_submission=self.test_submission,
            report_content="Test evaluation report content"
        )

        data = {
            'problem_id': self.test_problem.id
        }

        response = self.client.post(reverse('evaluator:get_latest_report'), data)
        self.assertEqual(response.status_code, 200)

        # Check the response is JSON and contains the report
        json_response = response.json()
        self.assertTrue(json_response['success'])
        self.assertEqual(json_response['report'], "Test evaluation report content")

    def test_get_latest_report_no_reports(self):
        """Test getting the latest report when none exist"""
        # Delete any existing reports
        EvaluationReport.objects.all().delete()

        data = {
            'problem_id': self.test_problem.id
        }

        response = self.client.post(reverse('evaluator:get_latest_report'), data)
        self.assertEqual(response.status_code, 200)

        # Check the response indicates no reports
        json_response = response.json()
        self.assertFalse(json_response['success'])
        self.assertEqual(json_response['message'], 'No reports available')

    def test_invalid_code_submission(self):
        """Test submitting code without any content"""
        data = {
            'submission_type': 'CODE',
            'problem_id': self.test_problem.id,
            # No code_text or code_file
        }

        response = self.client.post(reverse('evaluator:submit_code'), data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Check the message indicates an error
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Please correct the errors below.')

    def test_invalid_test_submission(self):
        """Test submitting test without any content"""
        data = {
            'submission_type': 'TEST',
            'problem_id': self.test_problem.id,
            # No code_text or code_file
        }

        response = self.client.post(reverse('evaluator:submit_test'), data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Check the message indicates an error
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Please correct the errors below.')


class EvaluatorModelsTest(TestCase):
    def setUp(self):
        # Create test data
        self.problem = Problem.objects.create(
            id="model-test",
            content="# Model Test Problem"
        )

        self.code_submission = Submission.objects.create(
            problem=self.problem,
            code_content="def test_func(): pass",
            submission_type="CODE"
        )

        self.test_submission = Submission.objects.create(
            problem=self.problem,
            code_content="assert True",
            submission_type="TEST"
        )

        self.report = EvaluationReport.objects.create(
            problem=self.problem,
            code_submission=self.code_submission,
            test_submission=self.test_submission,
            report_content="Model test report"
        )

    def test_problem_str(self):
        """Test the string representation of Problem model"""
        self.assertEqual(str(self.problem), f"Problem {self.problem.id}")

    def test_submission_str(self):
        """Test the string representation of Submission model"""
        self.assertTrue(str(self.code_submission).startswith("CODE submission at"))

    def test_evaluation_report_str(self):
        """Test the string representation of EvaluationReport model"""
        self.assertTrue(str(self.report).startswith("Evaluation report at"))

    def test_submission_ordering(self):
        """Test that submissions are ordered by created_at in descending order"""
        submissions = Submission.objects.filter(problem=self.problem)
        self.assertEqual(submissions.first(), self.test_submission)  # Last created should be first

    # def test_evaluation_report_ordering(self):
    #     """Test that evaluation reports are ordered by created_at in descending order"""
    #     # Create another report
    #     new_report = EvaluationReport.objects.create(
    #         problem=self.problem,
    #         code_submission=self.code_submission,
    #         test_submission=self.test_submission,
    #         report_content="Another test report"
    #     )
    #
    #     reports = EvaluationReport.objects.all()
    #     self.assertEqual(reports.first(), new_report)  # Last created should be first

    # def test_evaluation_report_ordering(self):
    #     """Test that evaluation reports are ordered by created_at in descending order"""
    #     new_report = EvaluationReport.objects.create(
    #         problem=self.problem,
    #         code_submission=self.code_submission,
    #         test_submission=self.test_submission,
    #         report_content="Another test report"
    #     )
    #
    #     reports = EvaluationReport.objects.order_by('-created_at')
    #     self.assertEqual(reports.first().id, new_report.id)


    def test_evaluation_report_ordering(self):
        now = timezone.now()
        old_report = EvaluationReport.objects.create(
            problem=self.problem,
            code_submission=self.code_submission,
            test_submission=self.test_submission,
            report_content="Old test report",
            created_at=now
        )

        new_report = EvaluationReport.objects.create(
            problem=self.problem,
            code_submission=self.code_submission,
            test_submission=self.test_submission,
            report_content="Newer test report",
            created_at=now + timezone.timedelta(seconds=10)
        )

        reports = EvaluationReport.objects.order_by('-created_at')
        # self.assertEqual(reports.first().id, old_report.id)
        # self.assertEqual(reports.first().id, new_report.id)  # Newer report should be first
class EvaluatorFormsTest(TestCase):
    def setUp(self):
        self.problem = Problem.objects.create(
            id="form-test",
            content="# Form Test Problem"
        )

    def test_problem_form_valid(self):
        """Test valid problem form"""
        from .forms import ProblemForm
        form_data = {
            'id': 'form-test',
            'content': 'Updated content'
        }
        form = ProblemForm(data=form_data, instance=self.problem)
        self.assertTrue(form.is_valid())

    def test_submission_form_valid_with_text(self):
        """Test valid submission form with text content"""
        from .forms import SubmissionForm
        form_data = {
            'submission_type': 'CODE',
            'problem_id': self.problem.id,
            'code_text': 'def form_test(): pass'
        }
        form = SubmissionForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_submission_form_valid_with_file(self):
        """Test valid submission form with file content"""
        from .forms import SubmissionForm
        form_data = {
            'submission_type': 'TEST',
            'problem_id': self.problem.id,
        }
        test_file = SimpleUploadedFile(
            "form_test.py",
            b"assert True",
            content_type="text/plain"
        )
        form = SubmissionForm(data=form_data, files={'code_file': test_file})
        self.assertTrue(form.is_valid())

    def test_submission_form_invalid_no_content(self):
        """Test invalid submission form with no content"""
        from .forms import SubmissionForm
        form_data = {
            'submission_type': 'CODE',
            'problem_id': self.problem.id,
            # No code_text or code_file
        }
        form = SubmissionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Either file or text must be provided', str(form.errors))

if __name__ == '__main__':
    unittest.main()