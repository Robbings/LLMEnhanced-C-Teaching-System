from datetime import timedelta

from django.utils import timezone

from Analysis.models import ProblemEvaluationReport, StudentSubmission, StageEvaluationReport
from Identity.models import User
from Identity.utils import getuserid, getrole
from LLM.Prompts.question_report import gen_report
from LLM.Prompts.report_gen_test import gen_test_report
import threading

from LLM.Prompts.stage_report import gen_stage_report

def async_create_problem_report(request, require_sample, submission):
    thread = threading.Thread(
        target=create_problem_report,
        args=(request, require_sample, submission)
    )
    thread.start()

def async_create_stage_report(request, user):
    """
    异步创建阶段报告
    :param request: HTTP请求对象
    :param user: 用户对象
    :return: None
    """
    thread = threading.Thread(target=create_stage_report, args=(request, user))
    thread.start()

def create_problem_report(request, require_sample, submission):
    """
    创建题目报告
    :param request: HTTP请求对象
    :param require_sample: 是否需要样例
    :param submission: 提交记录
    :return: None
    """
    if not submission:
        return None
    if getrole(request) != 'user':
        return None
    student = User.objects.get(uid=getuserid(request))
    code_content = submission.code_content
    problem = submission.problem_catalogue.problem_content
    problem_content = problem.content
    if code_content is None or code_content == '':
        # 从文件中读取代码内容
        if submission.code_file:
            with open(submission.code_file.path, 'r', encoding='utf-8') as file:
                code_content = file.read()
        else:
            code_content = ''
    if require_sample:
        sample_content = submission.sample_content
        if sample_content is None or sample_content == '':
            # 从文件中读取样例内容
            if submission.sample_file:
                with open(submission.sample_file.path, 'r', encoding='utf-8') as file:
                    sample_content = file.read()
            else:
                sample_content = ''
        report = gen_test_report({
            "question": problem_content,
            "code": code_content,
            "test_code": sample_content,
        })
    else:
        report = gen_report({
            "question": problem_content,
            "code": code_content,
        })

    if not report:
        return None

    # my_submission = StudentSubmission.objects.get(id=submission.id)
    # 保存报告到提交记录
    problemEvaluationReport = ProblemEvaluationReport.objects.create(
        user=student,
        problem=submission.problem_catalogue.problem_content,
        submission=submission,
        report_content=report
    )
    problemEvaluationReport.save()
    submission.status = 'passed'
    submission.score = 100  # 假设满分为100
    submission.test_total = 5
    submission.test_passed = 5  # 假设通过了一个测试用例
    submission.save()
    return problemEvaluationReport


def create_stage_report(request, user):
    """
    创建阶段报告
    :param request: HTTP请求对象
    :param user: 用户对象
    :return: StageEvaluationReport对象
    """
    # 获取该用户最近一次的阶段报告记录，没有则创建新的
    stage_report = StageEvaluationReport.objects.filter(user=user).order_by('-created_at').first()
    if stage_report is None:
        stage_report = StageEvaluationReport(user=user)
    stage_report.generate_state = 'pending'
    stage_report.save()
    # 获取用户最新一次提交记录
    latest_submission = StudentSubmission.objects.filter(student=user).order_by('-submitted_at').first()
    if latest_submission is None:
        stage_report.generate_state = 'completed'
        stage_report.report_content = "# 报告说明 \n\n > 该用户没有提交记录，无法生成阶段报告。\n\n"
        stage_report.save()
        return stage_report

    # 如果latest_submission时间与stage_report.end_date接近（避免误差），直接返回
    if stage_report.end_date and abs((latest_submission.submitted_at - stage_report.end_date).total_seconds()) < 3600:
        stage_report.generate_state = 'completed'
        stage_report.save()
        return stage_report

    # 获取最近一周的提交记录，最多10条
    one_week_ago = timezone.now() - timedelta(days=7)
    recent_submissions = StudentSubmission.objects.filter(
        student=user,
        submitted_at__gte=one_week_ago
    ).order_by('-submitted_at')[:5]

    if not recent_submissions:
        stage_report.generate_state = 'completed'
        stage_report.report_content = "# 报告说明 \n\n > 最近一周没有提交记录，无法生成阶段报告。\n\n"
        stage_report.save()
        return stage_report

    # 整理Markdown格式字符串
    markdown_content = "# 最近一周提交记录\n\n"
    for idx, submission in enumerate(recent_submissions, 1):
        problem = submission.problem_catalogue
        problem_content = problem.problem_content.content if problem.problem_content else "（无内容）"
        markdown_content += f"## 提交 {idx}\n"
        markdown_content += f"- **题目名称**: {problem.name}\n"
        markdown_content += f"- **题目内容**:\n\n{problem_content}\n\n"
        markdown_content += f"- **提交时间**: {submission.submitted_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        markdown_content += f"- **提交代码内容**:\n\n```\n{submission.code_content or '（无内容）'}\n```\n\n"
        markdown_content += f"- **提交测试用例代码内容**:\n\n```\n{submission.sample_content or '（无内容）'}\n```\n\n"

    # 调用 LLM 生成阶段报告
    generated_report = gen_stage_report(markdown_content)

    recent_submissions_list = list(recent_submissions)
    # 更新阶段报告
    if recent_submissions_list:
        stage_report.end_date = recent_submissions_list[0].submitted_at  # 最新
        stage_report.start_date = recent_submissions_list[-1].submitted_at  # 最早
    else:
        stage_report.end_date = None
        stage_report.start_date = None
    stage_report.generate_state = 'completed'
    stage_report.report_content = generated_report
    stage_report.save()

    return stage_report


if __name__ == "__main__":
    # 这里可以添加测试代码
    user = User.objects.get(uid='1')  # 替换为实际用户ID
    report = create_stage_report(None, user)
    print(report.report_content)  # 打印生成的阶段报告内容
