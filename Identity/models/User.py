from django.db import models


class User(models.Model):
    uid = models.AutoField(primary_key=True, verbose_name='ID')
    username = models.CharField(max_length=128, unique=True)
    # username = models.CharField(max_length=128, unique=True)
    password = models.CharField(max_length=256)
    email = models.EmailField(unique=True)
    c_time = models.DateTimeField(auto_now_add=True)
    has_confirmed = models.BooleanField(default=False)

    def __str__(self):
        return self.username

    class Meta:
        db_table = 't_user'
        app_label = 'identity'
        ordering = ["-c_time"]
        verbose_name = "用户"
        verbose_name_plural = "用户"
    # 有username、password、email、sex、birth(YYYYMMDD)，has_confirmed(是否已经确认)


# 确认码表
class ConfirmString(models.Model):
    code = models.CharField(max_length=256)
    user = models.OneToOneField('User', on_delete=models.CASCADE)
    c_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username + ":   " + self.code

    class Meta:
        db_table = 't_confirmstring'
        app_label = 'identity'
        ordering = ["-c_time"]
        verbose_name = "确认码"
        verbose_name_plural = "确认码"
