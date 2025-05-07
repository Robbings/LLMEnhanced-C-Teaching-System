from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
import json

from .models import Submission, EvaluationReport
from .forms import SubmissionForm
import test.myllm as myllm

def index(request):
    """Main view for the evaluator page"""
    code_form = SubmissionForm(initial={'submission_type': 'CODE'})
    test_form = SubmissionForm(initial={'submission_type': 'TEST'})

    code_submissions = Submission.objects.filter(submission_type='CODE').order_by('-created_at')[:5]
    test_submissions = Submission.objects.filter(submission_type='TEST').order_by('-created_at')[:5]
    latest_report = EvaluationReport.objects.first()

    context = {
        'code_form': code_form,
        'test_form': test_form,
        'code_submissions': code_submissions,
        'test_submissions': test_submissions,
        'latest_report': latest_report,
    }

    return render(request, 'evaluator/index.html', context)

@require_POST
def submit_code(request):
    """Handle code submission"""
    form = SubmissionForm(request.POST, request.FILES)

    if form.is_valid():
        submission = form.save(commit=False)

        if 'code_file' in request.FILES:
            submission.is_file = True
            file = request.FILES['code_file']
            submission.file_name = file.name
            # Read file content
            submission.code_content = file.read().decode('utf-8')
        else:
            submission.code_content = form.cleaned_data['code_text']

        submission.save()

        # Check if we have both code and test submissions to create a report
        # latest_test = Submission.objects.filter(submission_type='TEST').first()
        # if latest_test:
        #     create_evaluation_report(submission, latest_test)
        create_evaluation_report(submission)

        messages.success(request, 'Code submitted successfully!')
        return redirect('evaluator:index')

    messages.error(request, 'Please correct the errors below.')
    return redirect('evaluator:index')

@require_POST
def submit_test(request):
    """Handle test case submission"""
    form = SubmissionForm(request.POST, request.FILES)

    if form.is_valid():
        submission = form.save(commit=False)

        if 'code_file' in request.FILES:
            submission.is_file = True
            file = request.FILES['code_file']
            submission.file_name = file.name
            # Read file content
            submission.code_content = file.read().decode('utf-8')
        else:
            submission.code_content = form.cleaned_data['code_text']

        submission.save()

        # Check if we have both code and test submissions to create a report
        latest_code = Submission.objects.filter(submission_type='CODE').first()
        if latest_code:
            create_evaluation_report(latest_code, submission)

        messages.success(request, 'Test cases submitted successfully!')
        return redirect('evaluator:index')

    messages.error(request, 'Please correct the errors below.')
    return redirect('evaluator:index')

def create_code_evaluation_report(code_submission):
    state = {

    }

def create_evaluation_report(code_submission, test_submission):
    """Create an evaluation report from code and test submissions"""
    # Combine code and test case for LLM processing
    combined_input = f"""
CODE SUBMISSION:
{code_submission.code_content}

TEST CASES:
{test_submission.code_content}
"""

    # Generate report using LLM
    report_content = myllm.create_response(combined_input)

    # Save report
    report = EvaluationReport(
        code_submission=code_submission,
        test_submission=test_submission,
        report_content=report_content
    )
    report.save()

    return report

@require_POST
def get_latest_report(request):
    """API endpoint to get the latest evaluation report"""
    latest_report = EvaluationReport.objects.first()

    if latest_report:
        return JsonResponse({
            'success': True,
            'report': latest_report.report_content
        })

    return JsonResponse({
        'success': False,
        'message': 'No reports available'
    })
