
from django.urls import path
from . import views

app_name = 'evaluator'

urlpatterns = [
    path('', views.index, name='index'),
    path('submit/code/', views.submit_code, name='submit_code'),
    path('submit/test/', views.submit_test, name='submit_test'),
    path('report/latest/', views.get_latest_report, name='get_latest_report'),
]
