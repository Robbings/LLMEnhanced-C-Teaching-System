# 请求错误
import json

from django.http import HttpResponse


def request_error(msg='请求错误'):
    return HttpResponse(json.dumps({'code': 400, 'message': msg}, ensure_ascii=False))


# 请求成功
def request_success(msg='请求成功', data=None):
    if data == None:
        return HttpResponse(json.dumps({'code': 200, 'message': msg}, ensure_ascii=False))
    else:
        return HttpResponse(json.dumps({'code': 200, 'message': msg, 'data': data}, ensure_ascii=False))


#
def request_list_success(list, total=-1, listname='list', msg='获取成功'):
    if total == -1:
        return HttpResponse(json.dumps({'code': 200, 'message': msg, listname: list}, ensure_ascii=False),
                            content_type='application/json')
    return HttpResponse(json.dumps({'code': 200, 'message': msg, listname: list, 'total': total}, ensure_ascii=False),
                        content_type='application/json')
