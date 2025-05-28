from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
import json

from openai import models

from utils import getuserid, getrole
from .api.report import create_problem_report, async_create_problem_report, create_stage_report, \
    async_create_stage_report
from .models import ProblemEvaluationReport, Problem, ProblemCatalogue, StageEvaluationReport

import test.myllm as myllm
from Identity import models as id_models
from django.views.decorators.http import require_http_methods
from .forms import ProblemCatalogueForm

# 更新problem_list视图

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Q, Avg, Sum
from django.utils import timezone
import json
import markdown

from .models import ProblemCatalogue, StudentSubmission, ProblemEvaluationReport
from .forms import StudentSubmissionForm
from Identity.models import User, Teacher




@require_POST
def save_problem(request):
    """Handle problem saving"""
    problem_id = request.POST.get('id')
    content = request.POST.get('content')
    deadline = request.POST.get('deadline')
    problem_type = request.POST.get('problem_type', 0)  # Default to 0 if not provided
    requires_sample = request.POST.get('requires_sample', False)
    # 获取session信息
    if not request.session.get('is_login', None):
        return JsonResponse({
            'success': False,
            'message': 'You must be logged in to save a problem.'
        })
    uid = request.session.get('user_id', None)
    role = request.session.get('role', None)
    if not role or role not in ['teacher']:
        return JsonResponse({
            'success': False,
            'message': 'You do not have permission to save a problem.'
        })
    teacher = id_models.Teacher.objects.get(uid=uid)
    # 从teacher中获取到clazz
    clazz = teacher.clazz

    problem, created = Problem.objects.update_or_create(
        id=problem_id,
        defaults={'content': content}
    )

    ProblemCatalogue.objects.create(
        teacher=teacher,
        clazz=clazz,
        name=problem_id,
        deadline=deadline,
        problem_type=problem_type,
        problem_content=problem,
        requires_sample=requires_sample
    )

    return JsonResponse({
        'success': True,
        'message': 'Problem saved successfully',
        'problem_id': problem.id
    })


@require_POST
def get_problem(request):
    """API endpoint to get a problem by ID"""
    problem_id = request.POST.get('problem_id')

    try:
        problem = Problem.objects.get(id=problem_id)
        return JsonResponse({
            'success': True,
            'problem': {
                'id': problem.id,
                'content': problem.content
            }
        })
    except Problem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Problem not found'
        })


def create_evaluation_report(code_submission, test_submission, problem):
    """Create an evaluation report from code and test submissions"""
    # Combine problem, code and test case for LLM processing
    combined_input = f"""
PROBLEM:
{problem.content}

CODE SUBMISSION:
{code_submission.code_content}

TEST CASES:
{test_submission.code_content}
"""

    # Generate report using LLM
    report_content = myllm.create_response(combined_input)

    # Save report
    report = ProblemEvaluationReport(
        problem=problem,
        code_submission=code_submission,
        test_submission=test_submission,
        report_content=report_content
    )
    report.save()

    return report


@require_POST
def get_latest_report(request):
    """API endpoint to get the latest evaluation report"""
    problem_id = request.POST.get('problem_id')

    if problem_id:
        latest_report = ProblemEvaluationReport.objects.filter(problem_id=problem_id).first()
    else:
        latest_report = ProblemEvaluationReport.objects.first()

    if latest_report:
        return JsonResponse({
            'success': True,
            'report': latest_report.report_content
        })

    return JsonResponse({
        'success': False,
        'message': 'No reports available'
    })


# 出题


# @login_required #TODO 学习怎么使用login_required装饰器
def create_problem_view(request):
    """教师创建题目的视图"""
    if request.method == 'POST':
        form = ProblemCatalogueForm(request.POST)
        if form.is_valid():
            try:
                # 创建Problem对象
                problem = Problem.objects.create(
                    name= form.cleaned_data['name'],
                    content=form.cleaned_data['problem_content']
                )

                # 创建ProblemCatalogue对象
                catalogue = form.save(commit=False)
                uid = getuserid(request)
                teacher = id_models.Teacher.objects.get(uid=uid)
                catalogue.teacher = teacher
                catalogue.problem_content = problem
                catalogue.save()

                messages.success(request, '题目创建成功！')
                return redirect('analysis:problem_list')  # 重定向到题目列表页面

            except Exception as e:
                messages.error(request, f'创建题目时发生错误：{str(e)}')
        else:
            messages.error(request, '表单验证失败，请检查输入内容。')
    else:
        form = ProblemCatalogueForm()

    return render(request, 'teacher/create_problem.html', {'form': form})


# @require_http_methods(["GET"])
# def problem_list_view(request):
#     """题目列表视图"""
#     uid = getuserid(request)
#     teacher = id_models.Teacher.objects.get(uid=uid)
#     problems = ProblemCatalogue.objects.filter(teacher=teacher)
#     return render(request, 'teacher/problem_list.html', {'problems': problems})


@require_http_methods(["POST"])
def validate_problem_content(request):
    """AJAX验证题目内容"""
    try:
        data = json.loads(request.body)
        content = data.get('content', '')

        if len(content.strip()) < 10:
            return JsonResponse({
                'valid': False,
                'message': '题目内容至少需要10个字符'
            })

        return JsonResponse({
            'valid': True,
            'message': '题目内容格式正确'
        })
    except Exception as e:
        return JsonResponse({
            'valid': False,
            'message': '验证过程中发生错误'
        })


# NEW


# @login_required
def view_problem(request, problem_id):
    """查看题目详情"""
    problem = get_object_or_404(ProblemCatalogue, id=problem_id)

    # 判断用户类型
    role = getrole(request)
    uid = getuserid(request)
    if role == 'teacher':
        teacher = id_models.Teacher.objects.get(uid=uid)
        return view_problem_teacher(request, problem, teacher)
    elif role == 'user':
        student = id_models.User.objects.get(uid=uid)
        return view_problem_student(request, problem, student)
    else:
        messages.error(request, '无法确定用户身份')
        return redirect('Analysis:problem_list')


def view_problem_teacher(request, problem, teacher):
    """教师查看题目"""
    # 检查权限
    if problem.teacher != teacher:
        messages.error(request, '您没有权限查看此题目')
        return redirect('Analysis:problem_list')

    # 获取统计数据
    all_students = User.objects.filter(clazz=problem.clazz) if problem.clazz else User.objects.all()
    total_students = all_students.count()

    submissions = StudentSubmission.objects.filter(problem_catalogue=problem)
    total_submissions = submissions.count()
    passed_submissions = submissions.filter(status='passed').count()
    not_submitted_count = total_students - submissions.values('student').distinct().count()

    # 获取详细提交列表
    submission_details = []
    for student in all_students:
        try:
            submission = submissions.get(student=student)
        except StudentSubmission.DoesNotExist:
            submission = None

        submission_details.append({
            'student': student,
            'submission': submission,
            'has_report': ProblemEvaluationReport.objects.filter(
                user=student,
                problem=problem.problem_content
            ).exists() if submission else False
        })

    # 转换Markdown
    problem_html = markdown.markdown(problem.problem_content.content) if problem.problem_content else ""

    context = {
        'problem': problem,
        'problem_html': problem_html,
        'is_teacher': True,
        'stats': {
            'total_students': total_students,
            'total_submissions': total_submissions,
            'passed_submissions': passed_submissions,
            'not_submitted_count': not_submitted_count,
            'pass_rate': (passed_submissions / total_submissions * 100) if total_submissions > 0 else 0
        },
        'submission_details': submission_details,
    }

    return render(request, 'teacher/view_problem.html', context)


def view_problem_student(request, problem, student):
    """学生查看题目"""
    # 检查是否属于指定班级
    if problem.clazz and student.clazz != problem.clazz:
        messages.error(request, '您不在此题目的指定班级中')
        return redirect('Analysis:problem_list')

    # 获取学生的提交记录
    try:
        submission = StudentSubmission.objects.get(student=student, problem_catalogue=problem)
    except StudentSubmission.DoesNotExist:
        submission = None

    # 获取评测报告
    report = None
    if submission and problem.problem_content:
        try:
            report = ProblemEvaluationReport.objects.filter(
                user=student,
                problem=problem.problem_content
            ).latest('created_at')
        except ProblemEvaluationReport.DoesNotExist:
            pass

    # 转换Markdown
    problem_html = markdown.markdown(problem.problem_content.content) if problem.problem_content else ""

    # 检查是否过期
    is_expired = problem.deadline and timezone.now() > problem.deadline

    context = {
        'problem': problem,
        'problem_html': problem_html,
        'is_teacher': False,
        'submission': submission,
        'report': report,
        'is_expired': is_expired,
        'can_submit': not is_expired,
    }

    return render(request, 'teacher/view_problem.html', context)


# @login_required
def submit_problem(request, problem_id):
    """学生提交题目"""
    problem = get_object_or_404(ProblemCatalogue, id=problem_id)

    # 检查是否是学生
    try:
        student = id_models.User.objects.get(uid=getuserid(request))
    except:
        messages.error(request, '只有学生可以提交作业')
        return redirect('Analysis:view_problem', problem_id=problem_id)

    # 检查权限和截止时间
    if problem.clazz and student.clazz != problem.clazz:
        messages.error(request, '您不在此题目的指定班级中')
        return redirect('Analysis:view_problem', problem_id=problem_id)

    if problem.deadline and timezone.now() > problem.deadline:
        messages.error(request, '提交时间已过截止日期')
        return redirect('Analysis:view_problem', problem_id=problem_id)

    # 获取或创建提交记录
    submission, created = StudentSubmission.objects.get_or_create(
        student=student,
        problem_catalogue=problem,
        defaults={'status': 'pending'} # TODO： 设置默认状态
    )
    try:
        problemCatalogue = ProblemCatalogue.objects.get(id=problem_id)
    except ProblemCatalogue.DoesNotExist:
        messages.error(request, '题目不存在或已被删除')
        return redirect('Analysis:problem_list')

    if request.method == 'POST':
        form = StudentSubmissionForm(request.POST, request.FILES, instance=submission, problem=problem, problemCatalogue=problemCatalogue)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.status = 'pending'  # 重新设置为待评测
            submission.submitted_at = timezone.now()
            submission.save()

            messages.success(request, '提交成功！请等待系统评测。')

            # create_problem_report(request, problem.requires_sample, submission)
            async_create_problem_report(request, problem.requires_sample, submission)
            return redirect('Analysis:view_problem', problem_id=problem_id)
    else:
        form = StudentSubmissionForm(instance=submission, problem=problem)

    context = {
        'problem': problem,
        'form': form,
        'submission': submission,
    }


    return render(request, 'teacher/submit_problem.html', context)


# @login_required
def view_submission_code(request, submission_id):
    """查看提交的代码"""
    submission = get_object_or_404(StudentSubmission, id=submission_id)

    # 权限检查
    if getrole(request) != 'teacher':
        student = id_models.User.objects.filter(uid=getuserid(request)).first()
        if not (student and submission.student == student):
            messages.error(request, '您没有权限查看此提交')
            return redirect('Analysis:problem_list')
    elif getrole(request) == 'teacher':
        teacher = id_models.Teacher.objects.filter(uid=getuserid(request)).first()
        if not teacher:
            messages.error(request, '您没有权限查看此提交')
            return redirect('Analysis:problem_list')

    # 获取代码内容
    code_content = submission.code_content
    if submission.code_file and not code_content:
        try:
            with submission.code_file.open('r') as f:
                code_content = f.read()
        except:
            code_content = "无法读取文件内容"

    # 获取样例内容
    sample_content = submission.sample_content
    if submission.sample_file and not sample_content:
        try:
            with submission.sample_file.open('r') as f:
                sample_content = f.read()
        except:
            sample_content = "无法读取文件内容"

    context = {
        'submission': submission,
        'code_content': code_content,
        'sample_content': sample_content,
    }

    return render(request, 'teacher/view_submission_code.html', context)


# @login_required
# def view_report(request, submission_id):
#     """查看评测报告"""
#     submission = get_object_or_404(StudentSubmission, id=submission_id)
#
#     # 权限检查
#     if getrole(request) != 'teacher':
#         student = id_models.User.objects.filter(uid=getuserid(request)).first()
#         if not (student and submission.student == student):
#             messages.error(request, '您没有权限查看此报告')
#             return redirect('Analysis:problem_list')
#     elif getrole(request) == 'teacher':
#         teacher = id_models.Teacher.objects.filter(uid=getuserid(request)).first()
#         if not teacher:
#             messages.error(request, '您没有权限查看此报告')
#             return redirect('Analysis:problem_list')
#
#     # 获取报告
#     report = None
#     if submission.problem_catalogue.problem_content:
#         try:
#             report = ProblemEvaluationReport.objects.filter(
#                 user=submission.student,
#                 problem=submission.problem_catalogue.problem_content
#             ).latest('created_at')
#         except ProblemEvaluationReport.DoesNotExist:
#             pass
#
#     context = {
#         'submission': submission,
#         'report': report,
#     }
#
#     return render(request, 'teacher/view_report.html', context)

def view_report(request, submission_id):
    """查看评测报告"""
    submission = get_object_or_404(StudentSubmission, id=submission_id)

    # 权限检查
    if getrole(request) != 'teacher':
        student = id_models.User.objects.filter(uid=getuserid(request)).first()
        if not (student and submission.student == student):
            messages.error(request, '您没有权限查看此报告')
            return redirect('Analysis:problem_list')
    elif getrole(request) == 'teacher':
        teacher = id_models.Teacher.objects.filter(uid=getuserid(request)).first()
        if not teacher:
            messages.error(request, '您没有权限查看此报告')
            return redirect('Analysis:problem_list')

    # 获取报告
    report = None
    if submission.problem_catalogue.problem_content:
        try:
            report = ProblemEvaluationReport.objects.filter(
                user=submission.student,
                problem=submission.problem_catalogue.problem_content
            ).latest('created_at')
        except ProblemEvaluationReport.DoesNotExist:
            pass

    # 确保测试用例统计数据的完整性
    if not hasattr(submission, 'test_passed') or submission.test_passed is None:
        submission.test_passed = 0
    if not hasattr(submission, 'test_total') or submission.test_total is None:
        submission.test_total = 0
    if not hasattr(submission, 'score') or submission.score is None:
        submission.score = 0

    # 计算通过率
    if submission.test_total > 0:
        submission.pass_rate = (submission.test_passed / submission.test_total) * 100
    else:
        submission.pass_rate = 0

    context = {
        'submission': submission,
        'report': report,
    }

    return render(request, 'teacher/view_report.html', context)

# @login_required
def delete_problem(request, problem_id):
    """删除题目（仅教师）"""
    problem = get_object_or_404(ProblemCatalogue, id=problem_id)

    # 检查权限
    try:
        teacher = id_models.Teacher.objects.get(uid=getuserid(request))
        if problem.teacher != teacher:
            messages.error(request, '您没有权限删除此题目')
            return redirect('Analysis:problem_list')
    except:
        messages.error(request, '只有教师可以删除题目')
        return redirect('Analysis:problem_list')

    if request.method == 'POST':
        problem_name = problem.name
        problem.delete()
        messages.success(request, f'题目 "{problem_name}" 已成功删除')
        return redirect('Analysis:problem_list')

    # 这里预先计算通过数量
    passed_count = problem.student_submissions.filter(status='passed').count()

    context = {
        'problem': problem,
        'passed_count': passed_count,
    }
    return render(request, 'teacher/confirm_delete_problem.html', context)






# @login_required
def problem_list(request):
    """题目列表页面 - 教师和学生不同视图"""

    # 判断用户类型
    is_teacher = False
    is_student = False
    user_obj = None
    role = getrole(request)
    if role == 'teacher':
        user_obj = id_models.Teacher.objects.filter(uid=getuserid(request)).first()
        is_teacher = True
    elif role == 'user':
        user_obj = id_models.User.objects.filter(uid=getuserid(request)).first()
        is_student = True
    else:
        messages.error(request, '无法确定用户身份')
        return redirect('login')

    if is_teacher:
        return problem_list_teacher(request, user_obj)
    elif is_student:
        return problem_list_student(request, user_obj)


def problem_list_teacher(request, teacher):
    """教师题目列表"""
    # 获取教师创建的所有题目
    problems = ProblemCatalogue.objects.filter(teacher=teacher)

    # 为每个题目添加统计信息
    problem_stats = []
    for problem in problems:
        submissions = StudentSubmission.objects.filter(problem_catalogue=problem)
        total_submissions = submissions.count()
        passed_submissions = submissions.filter(status='passed').count()

        # 计算应该提交的学生总数
        if problem.clazz:
            total_students = User.objects.filter(clazz=problem.clazz).count()
        else:
            total_students = User.objects.count()

        submitted_students = submissions.values('student').distinct().count()
        not_submitted_count = total_students - submitted_students

        problem_stats.append({
            'problem': problem,
            'stats': {
                'total_students': total_students,
                'total_submissions': total_submissions,
                'passed_submissions': passed_submissions,
                'not_submitted_count': not_submitted_count,
                'submission_rate': (submitted_students / total_students * 100) if total_students > 0 else 0,
                'pass_rate': (passed_submissions / total_submissions * 100) if total_submissions > 0 else 0
            }
        })

    context = {
        'is_teacher': True,
        'problem_stats': problem_stats,
        'total_problems': problems.count(),
    }

    return render(request, 'teacher/problem_list.html', context)


def problem_list_student(request, student):
    """学生题目列表"""
    # 获取学生可以看到的题目（属于其班级或无班级限制）
    problems = ProblemCatalogue.objects.filter(
        Q(clazz='') | Q(clazz=student.clazz)
    ).order_by('-created_at')

    # 为每个题目添加学生的完成状态
    problem_status = []
    for problem in problems:
        # 获取学生对此题目的提交
        try:
            submission = StudentSubmission.objects.get(
                student=student,
                problem_catalogue=problem
            )
            status = submission.status
            submitted_at = submission.submitted_at
            score = submission.score
            pass_rate = submission.pass_rate
        except StudentSubmission.DoesNotExist:
            submission = None
            status = 'not_submitted'
            submitted_at = None
            score = 0
            pass_rate = 0

        # 检查是否有评测报告
        has_report = False
        if submission and problem.problem_content:
            has_report = ProblemEvaluationReport.objects.filter(
                user=student,
                problem=problem.problem_content
            ).exists()

        # 检查是否过期
        is_expired = problem.deadline and timezone.now() > problem.deadline

        problem_status.append({
            'problem': problem,
            'submission': submission,
            'status': status,
            'submitted_at': submitted_at,
            'score': score,
            'pass_rate': pass_rate,
            'has_report': has_report,
            'is_expired': is_expired,
            'can_submit': not is_expired
        })

    context = {
        'is_teacher': False,
        'problem_status': problem_status,
        'total_problems': problems.count(),
    }

    return render(request, 'teacher/problem_list.html', context)

def view_test(request):
    """测试视图"""
    # 这里可以放一些测试代码
    # 比如调用myllm的功能，或者其他逻辑
    user = id_models.User.objects.filter(uid=getuserid(request)).first()
    stage_report = create_stage_report(request, user)
    if stage_report:
        messages.success(request, '阶段报告创建成功！')
    else:
        messages.error(request, '阶段报告创建失败！')

        async_create_stage_report(request, user)
    return JsonResponse({
        'success': True,
        'message': '测试成功',
        'stage_report_id': stage_report.id if stage_report else None
    })


# 阶段报告

def stage_report_view(request):
    """阶段学习报告视图"""
    try:
        # 获取当前用户
        if getrole(request) == 'teacher':
            uid = request.GET.get('uid')
        else:
            uid = getuserid(request)
        user = id_models.User.objects.filter(uid=uid).first()

        if not user:
            return render(request, 'error.html', {'message': '用户不存在'})

        # 计算时间范围（过去一周）
        end_date = timezone.now()
        start_date = end_date - timedelta(days=7)

        stage_report = StageEvaluationReport.objects.filter(user=user).order_by('-created_at').first()
        if stage_report is None:
            stage_report = StageEvaluationReport(user=user)
        latest_submission = StudentSubmission.objects.filter(student=user).order_by('-submitted_at').first()
        if latest_submission is None:
            stage_report.generate_state = 'completed'
            stage_report.report_content = "# 报告说明 \n\n > 该用户没有提交记录，无法生成阶段报告。\n\n"
            stage_report.save()
        elif stage_report.end_date and abs(
                (latest_submission.submitted_at - stage_report.end_date).total_seconds()) < 3600:
            stage_report.generate_state = 'completed'
            stage_report.save()
        elif stage_report.generate_state != 'pending':
            async_create_stage_report(request, user)

        # 收集客观数据
        context_data = collect_stage_statistics(user, start_date, end_date)

        # 准备模板上下文
        context = {
            'user': user,
            'stage_report': stage_report,
            'start_date': start_date,
            'end_date': end_date,
            'is_teacher': getrole(request) == 'teacher',
            **context_data
        }

        return render(request, 'teacher/stage_report.html', context)

    except Exception as e:
        print(f"阶段报告视图错误: {e}")
        return render(request, 'error.html', {'message': '加载报告时发生错误'})


def collect_stage_statistics(user, start_date, end_date):
    """收集阶段统计数据"""
    try:
        # 获取时间范围内的提交记录
        submissions = StudentSubmission.objects.filter(
            student=user,
            submitted_at__gte=start_date,
            submitted_at__lte=end_date
        )

        # 提交统计
        commit_count = submissions.count()
        days_diff = (end_date - start_date).days
        avg_commits_per_day = commit_count / days_diff if days_diff > 0 else 0

        # 任务完成情况
        # 获取时间范围内涉及的问题目录
        clazz = user.clazz

        # 先筛出所有符合 clazz 的目录
        problem_catalogues = ProblemCatalogue.objects.filter(clazz=clazz)

        # 再按时间范围筛选
        if problem_catalogues.filter(created_at__lte=end_date, deadline__gte=start_date).exists():
            problem_catalogues = problem_catalogues.filter(created_at__lte=end_date, deadline__gte=start_date)
        else:
            problem_catalogues = problem_catalogues.filter(created_at__gte=start_date, created_at__lte=end_date)

        total_tasks = problem_catalogues.count()

        # 计算已完成任务（状态为passed的提交）
        completed_submissions = submissions.filter(status='passed')
        completed_tasks = completed_submissions.values('problem_catalogue').distinct().count()

        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        # 平均得分
        avg_score_data = submissions.aggregate(avg_score=Avg('score'))
        average_score = avg_score_data['avg_score'] if avg_score_data['avg_score'] else 0

        # 学习主题（从题目名称中提取）
        learning_topics = []
        if problem_catalogues.exists():
            topic_set = set()
            for catalogue in problem_catalogues:
                # 简单的主题提取逻辑，可以根据实际需求优化
                name_parts = catalogue.name.split()
                for part in name_parts:
                    if len(part) > 2:  # 过滤掉太短的词
                        topic_set.add(part)
            learning_topics = list(topic_set)[:6]  # 最多显示6个主题

        # 实际学习天数（有提交的天数）
        submission_dates = submissions.values_list('submitted_at__date', flat=True).distinct()
        study_days = len(set(submission_dates))

        return {
            'commit_count': commit_count,
            'avg_commits_per_day': avg_commits_per_day,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'completion_rate': completion_rate,
            'average_score': average_score,
            'learning_topics': learning_topics,
            'study_days': study_days,
        }

    except Exception as e:
        print(f"收集统计数据错误: {e}")
        return {
            'commit_count': 0,
            'avg_commits_per_day': 0,
            'total_tasks': 0,
            'completed_tasks': 0,
            'completion_rate': 0,
            'average_score': 0,
            'learning_topics': [],
            'study_days': 0,
        }



def check_stage_report_status(request):
    """检查阶段报告生成状态的API接口"""
    try:
        user = id_models.User.objects.filter(uid=getuserid(request)).first()
        if not user:
            return JsonResponse({'error': '用户不存在'}, status=404)

        stage_report = StageEvaluationReport.objects.filter(
            user=user
        ).order_by('-created_at').first()

        if not stage_report:
            return JsonResponse({'status': 'not_found'})

        return JsonResponse({
            'status': stage_report.generate_state,
            'created_at': stage_report.created_at.isoformat(),
            'has_content': bool(stage_report.report_content.strip()) if stage_report.report_content else False
        })

    except Exception as e:
        print(f"检查报告状态错误: {e}")
        return JsonResponse({'error': '服务器错误'}, status=500)


# 教师数据管理

def teacher_class_overview(request):
    """教师班级数据概览"""
    try:
        teacher = Teacher.objects.get(uid=getuserid(request))
    except Teacher.DoesNotExist:
        return render(request, 'error.html', {'message': '您没有教师权限'})

    teacher_class = teacher.clazz
    if not teacher_class:
        return render(request, 'teacher/teacher_class_overview.html', {
            'teacher': teacher,
            'students': [],
            'class_stats': {},
            'message': '您还未分配到任何班级'
        })

    students = User.objects.filter(clazz=teacher_class, has_confirmed=True)
    teacher_problems = ProblemCatalogue.objects.filter(teacher=teacher)

    class_stats = calculate_class_statistics(students, teacher_problems)

    student_data = []
    excellent_count = 0
    good_count = 0
    average_count = 0
    improve_count = 0

    for student in students:
        student_stats = calculate_student_statistics(student, teacher_problems)
        total_score = student_stats.get('total_score', 0)

        if total_score >= 90:
            excellent_count += 1
        elif total_score >= 80:
            good_count += 1
        elif total_score >= 60:
            average_count += 1
        else:
            improve_count += 1

        student_data.append({
            'student': student,
            'stats': student_stats
        })

    student_data.sort(key=lambda x: x['stats']['total_score'], reverse=True)

    total_students = len(student_data)
    active_count = class_stats.get('active_students', 0)
    inactive_count = total_students - active_count
    moderate_count = total_students - active_count - inactive_count  # 如果有中间层定义

    # 保证没有负数
    inactive_count = max(0, inactive_count)
    moderate_count = max(0, moderate_count)

    context = {
        'teacher': teacher,
        'teacher_class': teacher_class,
        'students': student_data,
        'class_stats': class_stats,
        'total_students': len(student_data),
        'teacher_problems_count': teacher_problems.count(),
        'excellent_count': excellent_count,
        'good_count': good_count,
        'average_count': average_count,
        'improve_count': improve_count,
        'active_count': active_count,
        'moderate_count': moderate_count,
        'inactive_count': inactive_count,

    }

    return render(request, 'teacher/teacher_class_overview.html', context)


def calculate_class_statistics(students, teacher_problems):
    """计算班级整体统计数据"""
    if not students.exists():
        return {
            'total_submissions': 0,
            'avg_score': 0,
            'completion_rate': 0,
            'active_students': 0,
            'total_problems': teacher_problems.count(),
        }

    # 获取所有学生的提交记录
    submissions = StudentSubmission.objects.filter(
        student__in=students,
        problem_catalogue__in=teacher_problems
    )

    # 计算统计数据
    total_submissions = submissions.count()
    avg_score = submissions.aggregate(avg_score=Avg('score'))['avg_score'] or 0

    # 计算完成率（有提交记录的学生比例）
    students_with_submissions = submissions.values('student').distinct().count()
    completion_rate = (students_with_submissions / students.count() * 100) if students.count() > 0 else 0

    # 计算活跃学生数（过去7天有提交的）
    week_ago = timezone.now() - timedelta(days=7)
    active_students = submissions.filter(
        submitted_at__gte=week_ago
    ).values('student').distinct().count()

    return {
        'total_submissions': total_submissions,
        'avg_score': round(avg_score, 1),
        'completion_rate': round(completion_rate, 1),
        'active_students': active_students,
        'total_problems': teacher_problems.count(),
    }


def calculate_student_statistics(student, teacher_problems):
    """计算单个学生的统计数据"""
    # 获取学生的提交记录
    submissions = StudentSubmission.objects.filter(
        student=student,
        problem_catalogue__in=teacher_problems
    )

    # 基础统计
    total_submissions = submissions.count()
    completed_problems = submissions.filter(status='passed').count()
    failed_problems = submissions.filter(status='failed').count()
    pending_problems = submissions.filter(status='pending').count()

    # 计算总分和平均分
    total_score = submissions.aggregate(total=Sum('score'))['total'] or 0
    avg_score = submissions.aggregate(avg=Avg('score'))['avg'] or 0

    # 计算完成率
    total_problems = teacher_problems.count()
    completion_rate = (completed_problems / total_problems * 100) if total_problems > 0 else 0

    # 计算通过率
    pass_rate = (completed_problems / total_submissions * 100) if total_submissions > 0 else 0

    # 最近活动时间
    last_submission = submissions.order_by('-submitted_at').first()
    last_activity = last_submission.submitted_at if last_submission else None

    # 计算本周提交数
    week_ago = timezone.now() - timedelta(days=7)
    week_submissions = submissions.filter(submitted_at__gte=week_ago).count()

    # 获取阶段报告状态
    stage_report = StageEvaluationReport.objects.filter(user=student).order_by('-created_at').first()
    report_status = stage_report.generate_state if stage_report else 'not_started'

    return {
        'total_submissions': total_submissions,
        'completed_problems': completed_problems,
        'failed_problems': failed_problems,
        'pending_problems': pending_problems,
        'total_score': total_score,
        'avg_score': round(avg_score, 1),
        'completion_rate': round(completion_rate, 1),
        'pass_rate': round(pass_rate, 1),
        'last_activity': last_activity,
        'week_submissions': week_submissions,
        'report_status': report_status,
        'total_problems': total_problems,
        'remaining_problems': total_problems - completed_problems,
    }


# @login_required
def student_detail_view(request, student_uid):
    """学生详细信息视图（可选的额外功能）"""
    try:
        teacher = Teacher.objects.get(uid=getuserid(request))
    except Teacher.DoesNotExist:
        return render(request, 'error.html', {'message': '您没有教师权限'})

    student = get_object_or_404(User, uid=student_uid, clazz=teacher.clazz)
    teacher_problems = ProblemCatalogue.objects.filter(teacher=teacher)

    # 获取学生的详细提交历史
    submissions = StudentSubmission.objects.filter(
        student=student,
        problem_catalogue__in=teacher_problems
    ).order_by('-submitted_at')

    student_stats = calculate_student_statistics(student, teacher_problems)

    context = {
        'teacher': teacher,
        'student': student,
        'submissions': submissions,
        'stats': student_stats,
    }

    return render(request, 'Analysis/student_detail.html', context)