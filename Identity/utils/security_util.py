import datetime
import hashlib
import json

from captcha.helpers import captcha_image_url
from captcha.models import CaptchaStore
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse

from Identity import models
from LLMEnhanced_C_Teaching_System.settings import (CONFIRM_EMAIL_HTML_CONTENT,HOST,
                                                    CONFIRM_DAYS,CONFIRM_EMIAL_SUBJECT,
                                                    CONFIRM_EMAIL_TEXT_CONTENT,EMAIL_HOST_USER)


##登录系统
def hash_code(s, salt='21371426'):
    h = hashlib.sha256()
    s += salt
    h.update(s.encode())
    return h.hexdigest()


def make_confirm_string(user):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    code = hash_code(user.username, now)
    models.ConfirmString.objects.create(code=code, user=user)
    return code


def send_email(email, code):
    html_content = CONFIRM_EMAIL_HTML_CONTENT.format(HOST, code, CONFIRM_DAYS)
    msg = EmailMultiAlternatives(CONFIRM_EMIAL_SUBJECT, CONFIRM_EMAIL_TEXT_CONTENT, EMAIL_HOST_USER, [email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()


# 验证系统
# 创建验证码
def new_captcha():
    hashkey = CaptchaStore.generate_key()  # 验证码答案
    # DEBUG:打印hashkey
    print(hashkey)
    image_url = captcha_image_url(hashkey)  # 验证码地址
    # image_url
    captcha = {'hashkey': hashkey, 'image_url': image_url}  # image_url
    return captcha


# 刷新验证码
def refresh_captcha(request):
    return HttpResponse(json.dumps(new_captcha()), content_type='application/json')


# 验证验证码
def jarge_captcha(captchaStr, captchaHashkey):
    if captchaStr and captchaHashkey:
        try:
            # 获取根据hashkey获取数据库中的response值
            get_captcha = CaptchaStore.objects.get(hashkey=captchaHashkey)
            if get_captcha.response == captchaStr.lower():  # 如果验证码匹配
                return True
        except:
            return False
    else:
        # 删除该条验证码
        CaptchaStore.objects.filter(hashkey=captchaHashkey).delete()
        return False


# session
# 登录
def setSession(request, roles):
    request.session['is_login'] = True
    if isinstance(roles, models.User):
        request.session['user_id'] = roles.uid
        request.session['user_name'] = roles.username
        request.session['role'] = 'user'
    elif isinstance(roles, models.Teacher):
        request.session['user_id'] = roles.uid
        request.session['user_name'] = roles.username
        request.session['role'] = 'teacher'
    else:
        raise Exception('roles类型错误')


def getrole(request):
    # handlers.role = request.session.get('role')
    return request.session.get('role')


# 获取用户id
def getuserid(request):
    # handlers.uid = request.session.get('user_id')
    return request.session.get('user_id')
