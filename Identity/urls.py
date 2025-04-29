from django.urls import path, include

from Identity import views
from .api import auth

urlpatterns = [
    # 身份认证部分
    path('login', auth.login),  # 登录
    path('refresh_captcha', auth.refresh_captcha),  # 刷新验证码
    path('captcha', include('captcha.urls')),  # 验证码地址
    # 1.用户部分
    path('register', auth.register),  # 注册
    path('confirm/', auth.user_confirm),  # 邮件确认
    path('user_login', auth.user_login),  # 登录
    path('logout', auth.logout),
    path('test', auth.test),  # 测试
]