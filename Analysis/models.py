# Analysis/models.py
from django.db import models
import uuid

class ProblemCatalogue(models.Model):
    """包含题目的创建者（外键teacher）、题目名称、创建时间、截止时间、题目类型（int）、是否需要样例(bool)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey('Identity.Teacher', on_delete=models.CASCADE, related_name='problem_catalogues')
    clazz = models.CharField(max_length=128, default='')  # Class or group associated with the catalogue
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField(null=True, blank=True)
    problem_type = models.IntegerField()  # Assuming problem_type is an integer
    problem_content = models.ForeignKey('Problem', on_delete=models.CASCADE, related_name='catalogues', null=True)
    requires_sample = models.BooleanField(default=False) # 是否需要样例

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Catalogue {self.name} by {self.teacher.email}"

class Problem(models.Model):
    """Model for problem statements"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Problem {self.id}"

class ProblemEvaluationReport(models.Model):
    """Model for evaluation reports"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('Identity.User', on_delete=models.CASCADE, related_name='evaluation_reports')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='reports', null=True)
    submission = models.ForeignKey('StudentSubmission', on_delete=models.CASCADE, related_name='evaluation_reports', null=True)
    report_content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    accept_rate = models.FloatField(default=0.0)  # 对LLM的接受度

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Evaluation report at {self.created_at}"

class StageEvaluationReport(models.Model):
    """Model for stage evaluation reports"""
    GEN__STATUS_CHOICES = [
        ('pending', '生成中'),
        ('completed', '已完成'),
        ('error', '生成错误'),
        ('not_started', '未开始'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('Identity.User', on_delete=models.CASCADE, related_name='stage_evaluation_reports')
    report_content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    generate_state = models.CharField(max_length=20, choices=GEN__STATUS_CHOICES, default='not_started')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Stage evaluation report at {self.created_at}"


class StudentSubmission(models.Model):
    """学生提交记录"""
    SUBMISSION_STATUS_CHOICES = [
        ('pending', '待评测'),
        ('passed', '通过'),
        ('failed', '未通过'),
        ('error', '错误'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey('Identity.User', on_delete=models.CASCADE, related_name='student_submissions')
    problem_catalogue = models.ForeignKey(ProblemCatalogue, on_delete=models.CASCADE,
                                          related_name='student_submissions')

    # 代码提交
    code_content = models.TextField(blank=True, null=True)
    code_file = models.FileField(upload_to='submissions/code/', blank=True, null=True)

    # 测试样例提交（如果需要）
    sample_content = models.TextField(blank=True, null=True)
    sample_file = models.FileField(upload_to='submissions/samples/', blank=True, null=True)

    # 提交状态和结果
    status = models.CharField(max_length=20, choices=SUBMISSION_STATUS_CHOICES, default='pending')
    score = models.IntegerField(default=0)  # 分数
    test_passed = models.IntegerField(default=0)  # 通过的测试用例数
    test_total = models.IntegerField(default=0)  # 总测试用例数

    # 执行结果
    execution_output = models.TextField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-submitted_at']
        # 每个学生对每个题目只能有一个最新提交
        unique_together = ['student', 'problem_catalogue']

    def __str__(self):
        return f"{self.student.username} - {self.problem_catalogue.name} - {self.status}"

    @property
    def is_passed(self):
        return self.status == 'passed'

    @property
    def pass_rate(self):
        if self.test_total > 0:
            return (self.test_passed / self.test_total) * 100
        return 0

    @pass_rate.setter
    def pass_rate(self, value):
        self._pass_rate = value


