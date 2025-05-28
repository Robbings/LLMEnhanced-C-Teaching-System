
from django.urls import path
from . import views

app_name = 'Analysis'

# urlpatterns = [
#     path('', views.index, name='index'),
#     path('submit/code/', views.submit_code, name='submit_code'),
#     path('submit/test/', views.submit_test, name='submit_test'),
#     path('problem/save/', views.save_problem, name='save_problem'),
#     path('problem/get/', views.get_problem, name='get_problem'),
#     path('report/latest/', views.get_latest_report, name='get_latest_report'),
#     # 创建题目页面
#     path('create-problem/', views.create_problem_view, name='create_problem'),
#
#     # 题目列表页面
#     path('problems/', views.problem_list_view, name='problem_list'),
#
#     # AJAX验证API
#     path('api/validate-content/', views.validate_problem_content, name='validate_content'),
# # 新增的URL配置
#     path('problems/<uuid:problem_id>/', views.view_problem, name='view_problem'),
#     path('problems/<uuid:problem_id>/submit/', views.submit_problem, name='submit_problem'),
#     path('problems/<uuid:problem_id>/delete/', views.delete_problem, name='delete_problem'),
#     path('submissions/<uuid:submission_id>/code/', views.view_submission_code, name='view_submission_code'),
#     path('submissions/<uuid:submission_id>/report/', views.view_report, name='view_report'),
#
# ]

urlpatterns = [
    # 原有的URL配置...
    path('problems/', views.problem_list, name='problem_list'),
    path('problems/create/', views.create_problem_view, name='create_problem'),

    # 新增的URL配置
    path('problems/<uuid:problem_id>/', views.view_problem, name='view_problem'),
    path('problems/<uuid:problem_id>/submit/', views.submit_problem, name='submit_problem'),
    path('problems/<uuid:problem_id>/delete/', views.delete_problem, name='delete_problem'),
    path('submissions/<uuid:submission_id>/code/', views.view_submission_code, name='view_submission_code'),
    path('submissions/<uuid:submission_id>/report/', views.view_report, name='view_report'),
    path('stage-report/', views.stage_report_view, name='stage_report'),
    path('api/stage-report-status/', views.check_stage_report_status, name='stage_report_status'),

    path('teacher/class-overview/', views.teacher_class_overview, name='teacher_class_overview'),
    path('teacher/student/<int:student_uid>/', views.student_detail_view, name='student_detail'),
    path('test/', views.view_test, name='test_code'),
]
