from django.db import models
import uuid


class Submission(models.Model):
    """Model for code submissions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code_content = models.TextField()
    is_file = models.BooleanField(default=False)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    submission_type = models.CharField(max_length=10, choices=[('CODE', 'Code'), ('TEST', 'Test Case')])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.submission_type} submission at {self.created_at}"


class EvaluationReport(models.Model):
    """Model for evaluation reports"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code_submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='code_reports')
    test_submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='test_reports')
    report_content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Evaluation report at {self.created_at}"