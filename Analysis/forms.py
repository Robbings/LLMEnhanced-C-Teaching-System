
from django import forms
from .models import StudentSubmission
# Analysis/forms.py
from django.utils import timezone
from .models import ProblemCatalogue

# class ProblemForm(forms.ModelForm):
#     class Meta:
#         model = Problem
#         fields = ['name', 'content']
#         widgets = {
#             'name': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
#             'content': forms.Textarea(attrs={'rows': 10, 'class': 'form-control', 'readonly': True}),
#         }
#
# class SubmissionForm(forms.ModelForm):
#     problem_id = forms.CharField(
#         widget=forms.HiddenInput(),
#         required=True
#     )
#     code_file = forms.FileField(required=False)
#     code_text = forms.CharField(widget=forms.Textarea, required=False)
#
#     class Meta:
#         model = Submission
#         fields = ['submission_type']
#         widgets = {
#             'submission_type': forms.HiddenInput(),
#         }
#
#     def clean(self):
#         cleaned_data = super().clean()
#         code_file = cleaned_data.get('code_file')
#         code_text = cleaned_data.get('code_text')
#
#         if not code_file and not code_text:
#             raise forms.ValidationError("Either file or text must be provided.")
#
#         return cleaned_data
#




class ProblemCatalogueForm(forms.ModelForm):
    # 自定义字段用于题目内容
    problem_content = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 15,
            'placeholder': '请输入Markdown格式的程序设计题目...\n\n例如：\n# 题目标题\n\n## 问题描述\n...',
            'class': 'form-control'
        }),
        label='题目内容（Markdown格式）',
        help_text='支持Markdown语法，请详细描述题目要求'
    )

    class Meta:
        model = ProblemCatalogue
        fields = ['name', 'clazz', 'deadline', 'problem_type', 'requires_sample']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入题目名称...'
            }),
            'clazz': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入班级或组别...'
            }),
            'deadline': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'problem_type': forms.Select(
                choices=[
                    (1, '任务分解（代码1）'),
                    (2, '代码编写（2）'),
                    (3, '整体训练（3）')
                ],
                attrs={'class': 'form-control'}
            ),
            'requires_sample': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'name': '题目名称',
            'clazz': '班级/组别',
            'deadline': '截止时间',
            'problem_type': '问题类型',
            'requires_sample': '是否需要编写测试样例'
        }
        help_texts = {
            'name': '请输入简洁明确的题目名称',
            'clazz': '指定题目适用的班级或学习组别',
            'deadline': '学生提交作业的最后期限',
            'problem_type': '根据教学目标选择合适的题目类型',
            'requires_sample': '勾选此项将要求学生提供测试样例'
        }

    def clean_deadline(self):
        deadline = self.cleaned_data.get('deadline')
        if deadline and deadline <= timezone.now():
            raise forms.ValidationError('截止时间必须晚于当前时间')
        return deadline

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if len(name.strip()) < 2:
            raise forms.ValidationError('题目名称至少需要2个字符')
        return name.strip()

    def clean_problem_content(self):
        content = self.cleaned_data.get('problem_content')
        if len(content.strip()) < 10:
            raise forms.ValidationError('题目内容至少需要10个字符')
        return content.strip()


## NEW

# forms.py 中添加的新表单

class StudentSubmissionForm(forms.ModelForm):
    # 代码提交选择
    code_input_method = forms.ChoiceField(
        choices=[('text', '文本输入'), ('file', '文件上传')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='text',
        label='代码提交方式'
    )

    # 样例提交选择（如果需要）
    sample_input_method = forms.ChoiceField(
        choices=[('text', '文本输入'), ('file', '文件上传')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='text',
        label='测试样例提交方式',
        required=False
    )

    class Meta:
        model = StudentSubmission
        fields = ['code_content', 'code_file', 'sample_content', 'sample_file']
        widgets = {
            'code_content': forms.Textarea(attrs={
                'rows': 15,
                'placeholder': '请输入您的代码...',
                'class': 'form-control font-monospace'
            }),
            'code_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.py,.cpp,.c,.java,.js,.txt'
            }),
            'sample_content': forms.Textarea(attrs={
                'rows': 8,
                'placeholder': '请输入测试样例，格式：\n输入1\n输出1\n输入2\n输出2\n...',
                'class': 'form-control font-monospace'
            }),
            'sample_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.txt,.in,.out'
            })
        }
        labels = {
            'code_content': '代码内容',
            'code_file': '代码文件',
            'sample_content': '测试样例',
            'sample_file': '样例文件'
        }

    def __init__(self, *args, **kwargs):
        self.problem = kwargs.pop('problem', None)
        self.problemCatalogue = kwargs.pop('problemCatalogue', None)
        super().__init__(*args, **kwargs)

        needs_sample = False
        if self.problemCatalogue:
            needs_sample = self.problemCatalogue.requires_sample

        if not needs_sample:
            self.fields['sample_input_method'].widget = forms.HiddenInput()
            self.fields['sample_content'].widget = forms.HiddenInput()
            self.fields['sample_file'].widget = forms.HiddenInput()
            self.fields['sample_content'].required = False
            self.fields['sample_file'].required = False

    def clean(self):
        cleaned_data = super().clean()
        code_method = cleaned_data.get('code_input_method')
        sample_method = cleaned_data.get('sample_input_method')

        # 验证代码提交
        if code_method == 'text':
            if not cleaned_data.get('code_content'):
                raise forms.ValidationError('请输入代码内容')
            # 清空文件字段
            cleaned_data['code_file'] = None
        elif code_method == 'file':
            if not cleaned_data.get('code_file'):
                raise forms.ValidationError('请上传代码文件')
            # 清空文本字段
            cleaned_data['code_content'] = ''

        # 验证样例提交（如果需要）
        needs_sample = False
        if self.problemCatalogue:
            needs_sample = self.problemCatalogue.requires_sample
        if needs_sample:
            if sample_method == 'text':
                if not cleaned_data.get('sample_content'):
                    raise forms.ValidationError('请输入测试样例')
                cleaned_data['sample_file'] = None
            elif sample_method == 'file':
                if not cleaned_data.get('sample_file'):
                    raise forms.ValidationError('请上传样例文件')
                cleaned_data['sample_content'] = ''

        return cleaned_data