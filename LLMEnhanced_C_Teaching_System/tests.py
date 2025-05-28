import json
from django.test import TestCase, RequestFactory, override_settings
from django.core import mail
from captcha.models import CaptchaStore
from Identity import models
from utils.security_util import (
    hash_code, make_confirm_string, send_email,
    new_captcha, refresh_captcha, judge_captcha,
    setSession, getrole, getuserid
)
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest


class IdentityUtilsTests(TestCase):
    def setUp(self):
        self.user = models.User.objects.create(username="testuser", password="123456")
        self.teacher = models.Teacher.objects.create(username="testteacher", password="123456")
        self.factory = RequestFactory()

    def add_session(self, request: HttpRequest):
        """给请求添加 session 支持"""
        middleware = SessionMiddleware(get_response=lambda r: None)
        middleware.process_request(request)
        request.session.save()

    def test_hash_code(self):
        result = hash_code("test")
        self.assertIsInstance(result, str)
        self.assertEqual(len(result), 64)

    def test_make_confirm_string(self):
        code = make_confirm_string(self.user)
        self.assertTrue(models.ConfirmString.objects.filter(code=code, user=self.user).exists())

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_email(self):
        code = "dummycode123"
        send_email("test@example.com", code)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("test@example.com", mail.outbox[0].to)

    def test_new_captcha(self):
        captcha = new_captcha()
        self.assertIn("hashkey", captcha)
        self.assertIn("image_url", captcha)
        self.assertTrue(CaptchaStore.objects.filter(hashkey=captcha['hashkey']).exists())

    def test_refresh_captcha(self):
        response = refresh_captcha(self.factory.get("/fake-url/"))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("hashkey", data)
        self.assertIn("image_url", data)

    def test_judge_captcha(self):
        captcha_obj = CaptchaStore.generate_key()
        captcha = CaptchaStore.objects.get(hashkey=captcha_obj)
        correct_response = captcha.response
        self.assertTrue(judge_captcha(correct_response, captcha.hashkey))
        self.assertFalse(judge_captcha("wrong", captcha.hashkey))
        self.assertFalse(judge_captcha(None, captcha.hashkey))

    def test_setSession_and_getrole_getuserid(self):
        request = self.factory.get("/")
        self.add_session(request)
        setSession(request, self.user)
        self.assertTrue(request.session['is_login'])
        self.assertEqual(getrole(request), 'user')
        self.assertEqual(getuserid(request), self.user.uid)

        request2 = self.factory.get("/")
        self.add_session(request2)
        setSession(request2, self.teacher)
        self.assertEqual(getrole(request2), 'teacher')
        self.assertEqual(getuserid(request2), self.teacher.uid)

    def test_setSession_invalid_role(self):
        request = self.factory.get("/")
        self.add_session(request)
        with self.assertRaises(Exception) as context:
            setSession(request, object())
        self.assertIn("roles类型错误", str(context.exception))
