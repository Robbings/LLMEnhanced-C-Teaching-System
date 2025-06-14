"""
Django settings for LLMEnhanced_C_Teaching_System project.

Generated by 'django-admin startproject' using Django 4.2.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-_f=#k$7q$x-$oe5rgo^stzw2l!bcm^@!_)j)+($$@4+u5c4w5#'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'Identity.apps.IdentityConfig',
    'Tasks.apps.TasksConfig',
    'Analysis.apps.AnalysisConfig',
    'captcha',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'LLMEnhanced_C_Teaching_System.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'LLMEnhanced_C_Teaching_System.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        # 导入mysql
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'cl_db',
        'USER': 'root',
        'PASSWORD': '123456',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET NAMES 'utf8mb4'",
        },
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = "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"
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGSMITH_PROJECT"] = "LLM-Clearning"
# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CAPTCHA验证码设置
# 字母验证码
CAPTCHA_IMAGE_SIZE = (80, 45)  # 设置 captcha 图片大小
CAPTCHA_LENGTH = 4  # 字符个数
CAPTCHA_TIMEOUT = 10  # 超时(minutes)#TODO：开发需要，上线时改为1分钟

# 加减乘除验证码
CAPTCHA_OUTPUT_FORMAT = '%(image)s %(text_field)s %(hidden_field)s '
CAPTCHA_NOISE_FUNCTIONS = ('captcha.helpers.noise_null',
                           'captcha.helpers.noise_arcs',  # 线
                           'captcha.helpers.noise_dots',  # 点
                           )
CAPTCHA_CHALLENGE_FUNCT = 'captcha.helpers.random_char_challenge'
# CAPTCHA_CHALLENGE_FUNCT = 'captcha.helpers.math_challenge'
# CAPTCHA_TIMEOUT = 1

# 跨域设置
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_HEADERS = ('*')

# 邮箱配置
# 邮箱配置
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.163.com'
EMAIL_PORT = 25
EMAIL_HOST_USER = 'robericklq@163.com'
EMAIL_HOST_PASSWORD = 'HHdxfj3286MaLBNf'
EMAIL_USE_TLS = False
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
CONFIRM_DAYS = 7

# 确认邮件常量表
HOST = '127.0.0.1:8000'
CONFIRM_EMIAL_SUBJECT = '大模型辅助教学系统注册确认邮件'
CONFIRM_EMAIL_TEXT_CONTENT = '''感谢您使用我们的大模型辅助教学系统，'''
CONFIRM_EMAIL_HTML_CONTENT = '''
<div style="font-family: 'Arial', sans-serif; color: #333; padding: 20px; background-color: #f9f9f9;">
    <h2 style="color: #4CAF50;">欢迎使用大模型辅助教学系统！</h2>
    <p>感谢您的注册，我们致力于提供以下功能来提升教学效率：</p>
    <ul>
        <li>任务分解</li>
        <li>代码生成</li>
        <li>测试样例生成</li>
    </ul>
    <p>请点击下面的按钮完成注册确认：</p>
    <p style="text-align: center; margin: 30px 0;">
        <a href="http://{}/user/confirm/?code={}" target="_blank" 
           style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px;">
           确认注册
        </a>
    </p>
    <p style="font-size: 14px; color: #777;">此链接有效期为 <strong>{}</strong> 天。请及时完成确认以正常使用系统功能。</p>
    <hr style="border: none; border-top: 1px solid #eee; margin: 40px 0;">
    <p style="font-size: 12px; color: #999;">如果您并未注册该系统，请忽略此邮件。</p>
</div>
'''


USE_AUTH = True

# 大模型配置
LLM_MODEL = "deepseek-v3"
LLM_MODEL_TOOL = "qwen-max"

# 项目路径 本文件路径的上级路径
PROJECT_PATH = "\\".join(os.path.dirname(os.path.abspath(__file__)).split('\\')[0:-1])
