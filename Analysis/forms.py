
from django import forms
from .models import Submission

class SubmissionForm(forms.ModelForm):
    code_file = forms.FileField(required=False)
    code_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 10, 'class': 'code-textarea'}),
        required=False
    )

    class Meta:
        model = Submission
        fields = ['submission_type']
        widgets = {
            'submission_type': forms.HiddenInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        code_file = cleaned_data.get('code_file')
        code_text = cleaned_data.get('code_text')

        if not code_file and not code_text:
            raise forms.ValidationError("Either file or text must be provided.")

        return cleaned_data
