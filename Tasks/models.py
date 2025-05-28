from django.db import models

# Create your models here.
class LLMData(models.Model):
    """存储大模型输出数据"""
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey('Identity.User', on_delete=models.CASCADE, related_name='llm_data')
    content = models.TextField()
    # 三种类型：任务分解、代码生成、测试代码生成
    data_type = models.CharField(max_length=50, choices=[
        ('task_decomposition', '任务分解'),
        ('code_generation', '代码生成'),
        ('test_code_generation', '测试代码生成')
    ])
    code_content = models.TextField(blank=True, null=True)  # 存储生成的代码内容
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"LLMData {self.id} by {self.user.email} at {self.created_at}"
