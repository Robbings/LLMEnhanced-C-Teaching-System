import json

from django.http import HttpResponse

from LLMEnhanced_C_Teaching_System.settings import USE_AUTH

'''  =============返回响应相关===========  '''


def _success_response(msg='', data_dict=None, code=200):
    if data_dict is None:
        return {
            'code': code,
            'message': msg
        }
    else:
        return {
            'code': code,
            'message': msg,
            **data_dict
        }


def _failed_response(msg='', code=400):
    return {
        'code': code,
        'message': msg
    }


def http_success_res(msg='', data_dict=None, code=200):
    success = _success_response(msg, data_dict, code)
    return HttpResponse(json.dumps(success, ensure_ascii=False),
                        content_type='application/json')


def http_failed_res(msg='', code=400):
    return HttpResponse(json.dumps(_failed_response(msg, code), ensure_ascii=False),
                        content_type='application/json')


def http_success_res_dict(data):
    # 如果data是一个字典，且code和message都存在
    if 'code' in data and 'message' in data:
        return HttpResponse(json.dumps(data, ensure_ascii=False), content_type='application/json')
    # 如果data是一个字典，但是code和message不存在
    if isinstance(data, dict):
        return HttpResponse(json.dumps(_success_response(data_dict=data), ensure_ascii=False),
                            content_type='application/json')
    # data不是一个字典
    return HttpResponse(json.dumps(_failed_response('服务器返回参数错误'), ensure_ascii=False),
                        content_type='application/json')


''' =============身份认证相关============ '''


def check_auth(request):
    if USE_AUTH and not request.session.get('is_login', None):
        return False
    return True


''' =============其他工具函数============'''


def mylen(tmp):
    return tmp, len(tmp)


def get_st_ed(request, total=100):
    pageIndex = request.GET.get('pageIndex')
    pageSize = request.GET.get('pageSize')
    if not pageIndex:
        pageIndex = 1
    if not pageSize:
        pageSize = total
    st = (int(pageIndex) - 1) * int(pageSize)
    ed = int(pageIndex) * int(pageSize)
    return st, ed
