
from django.utils import timezone
from datetime import timedelta

from django.shortcuts import render
from langchain.chat_models import init_chat_model

from Identity import models
from utils import *


def user_confirm(request):
    code = request.GET.get('code', None)
    message = ''
    status = 'error'
    try:
        confirm = models.ConfirmString.objects.get(code=code)
        # addLog(request, 'ConfirmString', 'Read', 'Check ConfirmString for ' + str(confirm.user.uid), 'ConfirmString')
    except:
        message = '无效的确认请求！'
        return render(request, 'tmp.html', locals())
    c_time = confirm.c_time
    now = datetime.datetime.now()
    # if now > c_time + datetime.timedelta(settings.CONFIRM_DAYS):
    if timezone.now() > (c_time + timedelta(days=settings.CONFIRM_DAYS)):
        confirm.user.dalete()
        message = '您的邮件已经过期！请重新注册!'
        return render(request, 'tmp.html', locals())
    else:
        confirm.user.has_confirmed = True
        confirm.user.save()
        confirm.delete()
        status = 'success'
        message = '感谢确认，请使用账户登录！'
        return render(request, 'tmp.html', locals())


##注册
def register(request):
    # 解析post方式传来的json表单，保存username、password、email、sex、birth(YYYYMMDD)
    # 打印request.POST
    print(request.POST)
    username = request.POST.get('username')
    password = request.POST.get('password')
    email = request.POST.get('email')
    sex = request.POST.get('sex')
    birthstr = request.POST.get('birth')
    # 如果上述信息不全，返回code=400，表示信息不全，并返回message
    if not all([username, password, email]):
        return HttpResponse(json.dumps({'code': 400, 'message': '信息不全'}, ensure_ascii=False),
                            content_type='application/json')
    # 将YYYYMMDD类型的birth转化为date
    try:
        birth = datetime.date(year=int(birthstr[0:4]), month=int(birthstr[4:6]), day=int(birthstr[6:8]))
    except:
        return HttpResponse(json.dumps({'code': 400, 'message': '生日格式错误'}, ensure_ascii=False),
                            content_type='application/json')
    # print(birth)
    if not birth or birth > datetime.date.today():
        return HttpResponse(json.dumps({'code': 400, 'message': '生日格式错误'}, ensure_ascii=False),
                            content_type='application/json')

    # 判断是否已经注册,数据库是mysql
    # addLog(request, 'Register', 'Read', 'Register for ' + str(username), 'User')
    if models.User.objects.filter(username=username):
        # 以json格式返回code=400，表示已经注册，并返回message
        return HttpResponse(json.dumps({'code': 400, 'message': '用户名已经存在'}, ensure_ascii=False),
                            content_type='application/json')
    if models.User.objects.filter(email=email):
        return HttpResponse(json.dumps({'code': 400, 'message': '该邮箱已经被注册了！'}, ensure_ascii=False),
                            content_type='application/json')
    # 如果没有注册，将数据保存到数据库
    new_user = models.User()
    new_user.username = username
    new_user.password = hash_code(password)
    new_user.birth = birth
    new_user.save()
    # 邮箱验证
    code = make_confirm_string(new_user)
    send_email(email, code)
    return HttpResponse(json.dumps({'code': 200, 'message': '注册成功'}, ensure_ascii=False),
                        content_type='application/json')


def user_login(request):
    if request.session.get('is_login', None):  # 不允许重复登录
        return HttpResponse(json.dumps({'code': 400, 'message': '已经登录'}, ensure_ascii=False),
                            content_type='application/json')
    request.session.flush()  # 清除session
    if request.method == 'POST':
        # 解析post方式传来的json表单，表单包含email、password、captcha、captchaHashkey
        # username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        captchaStr = request.POST.get('captchaCode')
        captchaHashkey = request.POST.get('captchaHashkey')
        debug = request.POST.get('debug')
        # 验证验证码
        if not debug or debug == False:
            if not jarge_captcha(captchaStr, captchaHashkey):
                # 刷新验证码
                captcha = new_captcha()
                return HttpResponse(
                    json.dumps({'code': 400, 'message': '验证码错误', 'captcha': captcha}, ensure_ascii=False),
                    content_type='application/json')
        # 验证用户名和密码
        # addLog(request, 'Login', 'Read', 'Login by ' + str(email), 'User')
        if models.User.objects.filter(email=email):
            user = models.User.objects.get(email=email)
            if user.password != hash_code(password):
                captcha = new_captcha()
                return HttpResponse(
                    json.dumps({'code': 400, 'message': '密码错误', 'captcha': captcha}, ensure_ascii=False),
                    content_type='application/json')
            elif not user.has_confirmed:
                captcha = new_captcha()
                return HttpResponse(json.dumps({'code': 400, 'message': '该用户还未通过邮件确认', 'captcha': captcha},
                                               ensure_ascii=False),
                                    content_type='application/json')
            else:
                setSession(request, user)
                # request.session['is_login'] = True
                # request.session['user_name'] = user.username
                # request.session['user_id'] = user.uid
                # request.session['role'] = 'user'
                return HttpResponse(json.dumps({'code': 200, 'message': '登录成功'}, ensure_ascii=False),
                                    content_type='application/json')
        else:
            captcha = new_captcha()
            return HttpResponse(
                json.dumps({'code': 400, 'message': '用户不存在', 'captcha': captcha}, ensure_ascii=False),
                content_type='application/json')
    else:
        return request_error()


# logout
def logout(request):
    if not request.session.get('is_login', None):
        return HttpResponse(json.dumps({'code': 400, 'message': '未登录'}, ensure_ascii=False),
                            content_type='application/json')
    request.session.flush()
    return HttpResponse(json.dumps({'code': 200, 'message': '退出成功'}, ensure_ascii=False),
                        content_type='application/json')


# 方便添加更多的角色
def login(request):
    # 只允许post
    if request.method != 'POST':
        return request_error()
    request.session.flush()
    # 解析role
    role = request.POST.get('role')
    if not role:
        return request_error('role不能为空')
    if role == 'user':
        return user_login(request)
    return request_error('role错误')


# 个人信息
# 获取个人信息
def get_info(request):
    # 只能get
    if request.method != 'GET':
        return request_error()
    # 如果没有登录，返回code=400，表示未登录
    # 如果有传入参数role和id
    role = request.GET.get('role')
    user_id = request.GET.get('id')
    if not role or not user_id:
        if not request.session.get('is_login', None):
            return HttpResponse(json.dumps({'code': 400, 'message': '未登录'}, ensure_ascii=False),
                                content_type='application/json')
        user_id = getuserid(request)
        role = getrole(request)

    if role == 'user':
        # addLog(request, 'get_info', 'Read', 'Read User ' + str(user_id), 'User')
        if not models.User.objects.filter(uid=user_id):
            return HttpResponse(json.dumps({'code': 400, 'message': '用户不存在'}, ensure_ascii=False),
                                content_type='application/json')
        user = {}
        user['username'] = models.User.objects.get(uid=user_id).username
        user['uid'] = user_id
        # user['birth'] = models.User.objects.get(uid=user_id).birth.strftime('%Y%m%d')
        # user['sex'] = models.User.objects.get(uid=user_id).sex
        user['email'] = models.User.objects.get(uid=user_id).email
        # print(user)
        return HttpResponse(json.dumps({'code': 200, 'message': '获取成功', 'user': user}, ensure_ascii=False),
                            content_type='application/json')
    else:
        return HttpResponse(json.dumps({'code': 400, 'message': '角色错误'}, ensure_ascii=False),
                            content_type='application/json')


def test(request):
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model = init_chat_model("deepseek-v3", model_provider="openai", base_url=base_url)
    from langchain_core.messages import HumanMessage, SystemMessage

    messages = [
        SystemMessage("Translate the following from English into Italian"),
        HumanMessage("hi!"),
    ]

    model.invoke(messages)

    for token in model.stream(messages):
        print(token.content, end="|")
    return HttpResponse(json.dumps({'code': 200, 'message': '测试成功'}, ensure_ascii=False),
                            content_type='application/json')