from lib2to3.fixes.fix_input import context

from django.shortcuts import render


def tmp(request):
    context = {
        'message': '恭喜您，注册成功！',
        'status': 'success',
    }
    return render(request, 'tmp.html', context)