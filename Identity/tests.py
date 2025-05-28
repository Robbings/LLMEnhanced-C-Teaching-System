import json
import datetime
from unittest.mock import patch, MagicMock

from captcha.models import CaptchaStore
from django.test import TestCase, Client
from django.conf import settings
from django.utils import timezone
from django.urls import reverse

from Identity.models import User, ConfirmString, Teacher
from utils import hash_code, make_confirm_string

from django.test import TestCase, RequestFactory, override_settings
from django.contrib.sessions.middleware import SessionMiddleware
from unittest.mock import patch, MagicMock
from django.http import JsonResponse

from Identity import models
from Identity.utils import security_util, util

class AuthTestCase(TestCase):
    def setUp(self):
        """
        设置测试环境，创建测试用户
        """
        self.client = Client()
        self.factory = RequestFactory()
        self.user = models.User.objects.create(username='testuser2', password='password')
        # 创建一个用户用于测试
        self.test_user = User.objects.create(
            username='testuser',
            password=hash_code('password123'),
            email='test@example.com',
            has_confirmed=True
        )

        # 创建一个教师用户用于测试
        self.test_teacher = Teacher.objects.create(
            username='testteacher',
            password=hash_code('password123'),
            email='test@example.com'
        )


        # 创建一个未确认的用户
        self.unconfirmed_user = User.objects.create(
            username='unconfirmed',
            password=hash_code('password123'),
            email='unconfirmed@example.com',
            has_confirmed=False
        )

        # 为未确认用户创建确认字符串
        self.confirm_code = make_confirm_string(self.unconfirmed_user)

    def test_register_user_success(self):
        """测试成功注册用户"""
        with patch('Identity.api.auth.send_email') as mock_send_email:
            mock_send_email.return_value = None

            data = {
                'username': 'newuser',
                'password': 'password123',
                'email': 'new@example.com',
            }

            response = self.client.post(reverse('register'), data=data)
            self.assertEqual(response.status_code, 200)

            content = json.loads(response.content)
            self.assertEqual(content['code'], 200)
            self.assertEqual(content['message'], '注册成功')

            # 验证用户是否创建
            user = User.objects.filter(username='newuser').first()
            self.assertIsNotNone(user)
            self.assertEqual(user.email, 'new@example.com')
            self.assertFalse(user.has_confirmed)

            # 确认是否调用了发送邮件函数
            mock_send_email.assert_called_once()

    def test_register_username_exists(self):
        """测试用户名已存在的情况"""
        data = {
            'username': 'testuser',  # 已存在的用户名
            'password': 'password123',
            'email': 'different@example.com',
        }

        response = self.client.post(reverse('register'), data=data)
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(content['code'], 400)
        self.assertEqual(content['message'], '用户名已经存在')

    def test_register_email_exists(self):
        """测试邮箱已被注册的情况"""
        data = {
            'username': 'differentuser',
            'password': 'password123',
            'email': 'test@example.com',  # 已存在的邮箱
        }

        response = self.client.post(reverse('register'), data=data)
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(content['code'], 400)
        self.assertEqual(content['message'], '该邮箱已经被注册了！')

    def test_register_missing_info(self):
        """测试信息不完整的情况"""
        data = {
            'username': 'newuser3',
            'password': 'password123',
            # 缺少 email
        }

        response = self.client.post(reverse('register'), data=data)
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(content['code'], 400)
        self.assertEqual(content['message'], '信息不全')

    def test_user_confirm_success(self):
        """测试成功确认用户"""
        response = self.client.get(reverse('confirm') + f'?code={self.confirm_code}')
        self.assertEqual(response.status_code, 200)

        # 验证用户是否已确认
        user = User.objects.get(username='unconfirmed')
        self.assertTrue(user.has_confirmed)

        # 验证确认字符串是否已删除
        self.assertEqual(ConfirmString.objects.filter(code=self.confirm_code).count(), 0)

    def test_user_confirm_invalid_code(self):
        """测试无效的确认代码"""
        response = self.client.get(reverse('confirm') + '?code=invalid_code')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '无效的确认请求！')

    def test_user_confirm_expired(self):
        """测试过期的确认代码"""
        # 创建一个过期的确认字符串
        expired_user = User.objects.create(
            username='expired',
            password=hash_code('password123'),
            email='expired@example.com',
            has_confirmed=False
        )

        confirm = ConfirmString(
            code='expired_code',
            user=expired_user
        )
        confirm.save()
        ConfirmString.objects.filter(code='expired_code').update(c_time=timezone.now() - timezone.timedelta(days=settings.CONFIRM_DAYS + 10))

        with patch('Identity.models.User.delete') as mock_delete:
            mock_delete.return_value = None

            response = self.client.get(reverse('confirm') + '?code=expired_code')
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, '您的邮件已经过期！请重新注册!')

            # 确认删除方法被调用
            mock_delete.assert_called_once()

    @patch('Identity.api.auth.judge_captcha')
    def test_user_login_success(self, mock_judge_captcha):
        """测试成功登录"""
        mock_judge_captcha.return_value = True

        data = {
            'email': 'test@example.com',
            'password': 'password123',
            'captchaCode': 'ABCD',
            'captchaHashkey': 'hashkey',
            'role': 'user'
        }

        response = self.client.post(reverse('login'), data=data)
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(content['code'], 200)
        self.assertEqual(content['message'], '登录成功')

        # 验证会话状态
        session = self.client.session
        self.assertTrue(session.get('is_login'))
        self.assertEqual(session.get('user_name'), 'testuser')
        self.assertEqual(session.get('user_id'), self.test_user.uid)

    def test_login_no_role(self):
        data = {
            'email': 'test@example.com',
            'password': 'password123',
            'captchaCode': 'ABCD',
            'captchaHashkey': 'hashkey',
        }
        response = self.client.post(reverse('login'), data=data)
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(content['code'], 400)
        self.assertEqual(content['message'], 'role不能为空')

    def test_login_error_role(self):
        data = {
            'email': 'test@example.com',
            'password': 'password123',
            'captchaCode': 'ABCD',
            'captchaHashkey': 'hashkey',
            'role': 'invalid_role'  # 无效角色
        }
        response = self.client.post(reverse('login'), data=data)
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(content['code'], 400)
        self.assertEqual(content['message'], 'role错误')

    # 重复登录、get登录
    @patch('Identity.api.auth.judge_captcha')
    @patch('Identity.api.auth.new_captcha')
    def test_user_login_wrong_password(self, mock_new_captcha, mock_judge_captcha):
        """测试密码错误的情况"""
        mock_judge_captcha.return_value = True
        mock_new_captcha.return_value = {'hashkey': 'newhashkey', 'image_url': 'url'}

        data = {
            'email': 'test@example.com',
            'password': 'wrongpassword',
            'captchaCode': 'ABCD',
            'captchaHashkey': 'hashkey',
            'role': 'user'
        }

        response = self.client.post(reverse('login'), data=data)
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(content['code'], 400)
        self.assertEqual(content['message'], '密码错误')
        self.assertIn('captcha', content)

    @patch('Identity.api.auth.judge_captcha')
    @patch('Identity.api.auth.new_captcha')
    def test_user_login_unconfirmed(self, mock_new_captcha, mock_judge_captcha):
        """测试未确认用户登录"""
        mock_judge_captcha.return_value = True
        mock_new_captcha.return_value = {'hashkey': 'newhashkey', 'image_url': 'url'}

        data = {
            'email': 'unconfirmed@example.com',
            'password': 'password123',
            'captchaCode': 'ABCD',
            'captchaHashkey': 'hashkey',
            'role': 'user'
        }

        response = self.client.post(reverse('login'), data=data)
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(content['code'], 400)
        self.assertEqual(content['message'], '该用户还未通过邮件确认')
        self.assertIn('captcha', content)

    @patch('Identity.api.auth.judge_captcha')
    @patch('Identity.api.auth.new_captcha')
    def test_user_login_user_not_exist(self, mock_new_captcha, mock_judge_captcha):
        """测试用户不存在的情况"""
        mock_judge_captcha.return_value = True
        mock_new_captcha.return_value = {'hashkey': 'newhashkey', 'image_url': 'url'}

        data = {
            'email': 'nonexistent@example.com',
            'password': 'password123',
            'captchaCode': 'ABCD',
            'captchaHashkey': 'hashkey',
            'role': 'user'
        }

        response = self.client.post(reverse('login'), data=data)
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(content['code'], 400)
        self.assertEqual(content['message'], '用户不存在')
        self.assertIn('captcha', content)

    @patch('Identity.api.auth.judge_captcha')
    @patch('Identity.api.auth.new_captcha')
    def test_user_login_captcha_error(self, mock_new_captcha, mock_judge_captcha):
        """测试验证码错误的情况"""
        mock_judge_captcha.return_value = False
        mock_new_captcha.return_value = {'hashkey': 'newhashkey', 'image_url': 'url'}

        data = {
            'email': 'test@example.com',
            'password': 'password123',
            'captchaCode': 'WRONG',
            'captchaHashkey': 'hashkey',
            'role': 'user'
        }

        response = self.client.post(reverse('login'), data=data)
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(content['code'], 400)
        self.assertEqual(content['message'], '验证码错误')
        self.assertIn('captcha', content)


    def test_user_login_already_logged_in(self):
        """测试已登录用户再次登录"""
        # 先登录
        session = self.client.session
        session['is_login'] = True
        session.save()

        data = {
            'email': 'test@example.com',
            'password': 'password123',
            'debug': 'True',
            'role': 'user'
        }

        response = self.client.post(reverse('login'), data=data)
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(content['code'], 400)
        self.assertEqual(content['message'], '已经登录')

    def test_logout_success(self):
        """测试成功登出"""
        # 先登录
        session = self.client.session
        session['is_login'] = True
        session['user_name'] = 'testuser'
        session['user_id'] = self.test_user.uid
        session.save()

        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(content['code'], 200)
        self.assertEqual(content['message'], '退出成功')

        # 验证会话状态
        session = self.client.session
        self.assertIsNone(session.get('is_login'))

    def test_logout_not_logged_in(self):
        """测试未登录状态下登出"""
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(content['code'], 400)
        self.assertEqual(content['message'], '未登录')

#
#     def test_login_router_invalid_role(self):
#         """测试通过login路由使用无效角色"""
#         data = {
#             'role': 'invalid',
#             'email': 'test@example.com',
#             'password': 'password123'
#         }
#
#         response = self.client.post(reverse('login'), data=data)
#         self.assertEqual(response.status_code, 200)
#
#         content = json.loads(response.content)
#         self.assertEqual(content['code'], 400)
#         self.assertEqual(content['message'], 'role错误')
#
#     def test_login_router_missing_role(self):
#         """测试通过login路由缺少角色参数"""
#         data = {
#             'email': 'test@example.com',
#             'password': 'password123'
#         }
#
#         response = self.client.post(reverse('login'), data=data)
#         self.assertEqual(response.status_code, 200)
#
#         content = json.loads(response.content)
#         self.assertEqual(content['code'], 400)
#         self.assertEqual(content['message'], 'role不能为空')

    def test_login_router_get_method(self):
        """测试通过GET方法访问login路由"""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(content['code'], 400)
        self.assertEqual(content['message'], '请求错误')

    def test_get_info_logged_in(self):
        """测试登录用户获取自己的信息"""
        # 先登录
        session = self.client.session
        session['is_login'] = True
        session['user_name'] = 'testuser'
        session['user_id'] = self.test_user.uid
        session['role'] = 'user'
        session.save()

        response = self.client.get(reverse('get_info'))
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(content['code'], 200)
        self.assertEqual(content['message'], '获取成功')
        self.assertEqual(content['user']['username'], 'testuser')
        self.assertEqual(content['user']['email'], 'test@example.com')

    def test_get_info_not_logged_in(self):
        """测试未登录用户获取信息"""
        response = self.client.get(reverse('get_info'))
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(content['code'], 400)
        self.assertEqual(content['message'], '未登录')

    def test_get_info_with_params(self):
        """测试通过参数获取特定用户信息"""
        response = self.client.get(reverse('get_info') + f'?role=user&id={self.test_user.uid}')
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(content['code'], 200)
        self.assertEqual(content['message'], '获取成功')
        self.assertEqual(content['user']['username'], 'testuser')
        self.assertEqual(content['user']['email'], 'test@example.com')

    def test_get_info_invalid_user(self):
        """测试获取不存在用户的信息"""
        response = self.client.get(reverse('get_info') + '?role=user&id=999')
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(content['code'], 400)
        self.assertEqual(content['message'], '用户不存在')

    def test_get_info_invalid_role(self):
        """测试获取无效角色的信息"""
        response = self.client.get(reverse('get_info') + f'?role=invalid&id={self.test_user.uid}')
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(content['code'], 400)
        self.assertEqual(content['message'], '角色错误')

    def test_get_info_post_method(self):
        """测试通过POST方法访问get_info路由"""
        response = self.client.post(reverse('get_info'))
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(content['code'], 400)
        self.assertEqual(content['message'], '请求错误')

    def _add_session_to_request(self, request):
        middleware = SessionMiddleware(lambda req: None)  # 传一个空的 get_response 函数
        middleware.process_request(request)
        request.session.save()

    def test_hash_code(self):
        result = security_util.hash_code("test")
        self.assertIsInstance(result, str)
        self.assertEqual(len(result), 64)

    def test_make_confirm_string(self):
        code = security_util.make_confirm_string(self.user)
        self.assertEqual(len(code), 64)
        self.assertTrue(models.ConfirmString.objects.filter(code=code).exists())

    @patch('Identity.utils.security_util.EmailMultiAlternatives')
    def test_send_email(self, mock_email):
        mock_instance = MagicMock()
        mock_email.return_value = mock_instance
        security_util.send_email('test@example.com', 'testcode')
        mock_email.assert_called_once()
        mock_instance.send.assert_called_once()

    @patch('Identity.utils.security_util.CaptchaStore.generate_key', return_value='testkey')
    @patch('Identity.utils.security_util.captcha_image_url', return_value='/captcha/testkey/')
    def test_new_captcha(self, mock_url, mock_key):
        result = security_util.new_captcha()
        self.assertEqual(result['hashkey'], 'testkey')
        self.assertEqual(result['image_url'], '/captcha/testkey/')

    @patch('Identity.utils.security_util.new_captcha', return_value={'hashkey': 'key', 'image_url': '/url'})
    def test_refresh_captcha(self, mock_new_captcha):
        request = self.factory.get('/refresh-captcha/')
        response = security_util.refresh_captcha(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('hashkey', response.content.decode())

    def test_jarge_captcha_valid(self):
        captcha = CaptchaStore.objects.create(response='abcd')
        result = security_util.jarge_captcha('abcd', captcha.hashkey)
        self.assertTrue(result)

    def test_jarge_captcha_invalid(self):
        result = security_util.jarge_captcha('abcd', 'nonexistent')
        self.assertFalse(result)

    def test_set_session_user(self):
        request = self.factory.get('/')
        self._add_session_to_request(request)
        security_util.setSession(request, self.user)
        self.assertTrue(request.session['is_login'])
        self.assertEqual(request.session['role'], 'user')

    def test_getrole(self):
        request = self.factory.get('/')
        self._add_session_to_request(request)
        request.session['role'] = 'user'
        self.assertEqual(security_util.getrole(request), 'user')

    def test_getuserid(self):
        request = self.factory.get('/')
        self._add_session_to_request(request)
        request.session['user_id'] = 123
        self.assertEqual(security_util.getuserid(request), 123)

    def test_http_success_res(self):
        response = util.http_success_res("ok", {'data': 'value'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('data', response.content.decode())

    def test_http_failed_res(self):
        response = util.http_failed_res("error")
        self.assertEqual(response.status_code, 200)
        self.assertIn('error', response.content.decode())

    def test_http_success_res_dict_complete(self):
        response = util.http_success_res_dict({'code': 200, 'message': 'ok'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('ok', response.content.decode())

    def test_http_success_res_dict_data_only(self):
        response = util.http_success_res_dict({'foo': 'bar'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('foo', response.content.decode())

    def test_http_success_res_dict_non_dict(self):
        response = util.http_success_res_dict("not a dict")
        self.assertEqual(response.status_code, 200)
        self.assertIn('服务器返回参数错误', response.content.decode())






#     @patch('Identity.api.auth.make_confirm_string')
#     @patch('Identity.api.auth.send_email')
#     @patch('random.randint')
#     def test_test_endpoint(self, mock_randint, mock_send_email, mock_make_confirm_string):
#         """测试test端点"""
#         mock_randint.side_effect = [1234, 5678, 9012]  # 随机数序列
#         mock_make_confirm_string.return_value = 'test_confirm_code'
#         mock_send_email.return_value = None
#
#         response = self.client.get(reverse('test'))
#         self.assertEqual(response.status_code, 200)
#
#         content = json.loads(response.content)
#         self.assertEqual(content['code'], 200)
#         self.assertEqual(content['message'], '测试成功')
#
#         # 验证是否创建了测试用户
#         user = User.objects.filter(username='test123456789012').first()
#         self.assertIsNotNone(user)
#         self.assertEqual(user.email, 'test1234@qq.com')
#
#         # 验证是否调用了make_confirm_string和send_email
#         mock_make_confirm_string.assert_called_once()
#         mock_send_email.assert_called_once_with('1700325132@qq.com', 'test_confirm_code')
#
#
# class CaptchaTestCase(TestCase):
#     def setUp(self):
#         """设置测试环境"""
#         self.client = Client()
#
#     def test_refresh_captcha(self):
#         """测试刷新验证码功能"""
#         response = self.client.get(reverse('refresh_captcha'))
#         self.assertEqual(response.status_code, 200)
#
#         content = json.loads(response.content)
#         self.assertEqual(content['code'], 200)
#         self.assertEqual(content['message'], '验证码刷新成功')
#         self.assertIn('captcha', content)
#         self.assertIn('hashkey', content['captcha'])
#         self.assertIn('image_url', content['captcha'])
#
#
# class ModelTestCase(TestCase):
#     def setUp(self):
#         """设置测试环境，创建测试用户"""
#         self.test_user = User.objects.create(
#             username='modeltest',
#             password=hash_code('password123'),
#             email='modeltest@example.com',
#             birth=datetime.date(1990, 1, 1),
#             has_confirmed=True
#         )
#
#     def test_user_model(self):
#         """测试用户模型的创建和字段"""
#         user = User.objects.get(username='modeltest')
#         self.assertEqual(user.email, 'modeltest@example.com')
#         self.assertEqual(user.password, hash_code('password123'))
#         self.assertEqual(user.birth, datetime.date(1990, 1, 1))
#         self.assertTrue(user.has_confirmed)
#         self.assertIsNotNone(user.uid)
#         self.assertIsNotNone(user.c_time)
#
#     def test_confirm_string_model(self):
#         """测试确认字符串模型的创建和字段"""
#         confirm_code = make_confirm_string(self.test_user)
#
#         # 获取创建的确认字符串
#         confirm_string = ConfirmString.objects.get(user=self.test_user)
#         self.assertEqual(confirm_string.code, confirm_code)
#         self.assertIsNotNone(confirm_string.c_time)
#
#         # 测试关联关系
#         self.assertEqual(confirm_string.user.username, 'modeltest')
#
#     def test_unique_constraints(self):
#         """测试唯一性约束"""
#         # 测试用户名唯一性
#         with self.assertRaises(Exception):
#             User.objects.create(
#                 username='modeltest',  # 已存在的用户名
#                 password='different_password',
#                 email='different@example.com',
#                 birth=datetime.date(1990, 1, 1)
#             )
#
#         # 测试邮箱唯一性
#         with self.assertRaises(Exception):
#             User.objects.create(
#                 username='different_user',
#                 password='different_password',
#                 email='modeltest@example.com',  # 已存在的邮箱
#                 birth=datetime.date(1990, 1, 1)
#             )