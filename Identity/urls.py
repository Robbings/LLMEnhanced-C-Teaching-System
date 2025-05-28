from django.urls import path, include

from Identity import views
from .api import auth

urlpatterns = [
    # 身份认证部分
    path('login', auth.login, name='login'),  # 登录
    path('refresh_captcha', auth.refresh_captcha, name='refresh_captcha'),  # 刷新验证码
    path('captcha', include('captcha.urls'), name='captcha'),  # 验证码地址
    # 1.用户部分
    path('register', auth.register, name='register'),  # 注册
    path('confirm/', auth.user_confirm, name='confirm'),  # 邮件确认
    path('logout', auth.logout, name='logout'),
    # path('test', auth.test),  # 测试
    path('info', auth.get_info, name='get_info'),  # 获取个人信息
    path('', views.index, name='index')
]