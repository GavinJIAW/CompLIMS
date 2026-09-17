# -*- coding: utf-8 -*-


import logging
import traceback

from django.db.models import ProtectedError
from django.http import Http404
from rest_framework.exceptions import (
    APIException as DRFAPIException, AuthenticationFailed, NotAuthenticated,
    ValidationError, PermissionDenied, NotFound,
)
from rest_framework.status import HTTP_401_UNAUTHORIZED
from rest_framework.views import set_rollback, exception_handler

from coreadmin.utils.json_response import ErrorResponse

logger = logging.getLogger(__name__)


class CustomAuthenticationFailed(NotAuthenticated):
    # 设置 status_code 属性为 400
    status_code = 400

def CustomExceptionHandler(ex, context):
    """
    统一异常拦截处理
    目的:(1)取消所有的500异常响应,统一响应为标准错误返回
        (2)准确显示错误信息
    :param ex:
    :param context:
    :return:
    """
    msg = ''
    code = 4000
    # 调用默认的异常处理函数
    response = exception_handler(ex, context)
    # Keep DRF security statuses and headers while retaining the project envelope.
    if isinstance(ex, (ValidationError, PermissionDenied, NotFound, NotAuthenticated,
                       AuthenticationFailed, Http404)):
        status = response.status_code if response is not None else 404
        if isinstance(ex, (NotAuthenticated, AuthenticationFailed)):
            status = HTTP_401_UNAUTHORIZED
        return ErrorResponse(
            msg=response.data if response is not None else "Not found",
            code=401 if status == 401 else 4000,
            status=status,
            headers=dict(response.headers) if response is not None else None,
        )
    if isinstance(ex, DRFAPIException):
        set_rollback()
        msg = ex.detail
        if isinstance(msg,dict):
            for k, v in msg.items():
                for i in v:
                    msg = "%s:%s" % (k, i)
    elif isinstance(ex, ProtectedError):
        set_rollback()
        msg = "删除失败:该条数据与其他数据有相关绑定"
    # elif isinstance(ex, DatabaseError):
    #     set_rollback()
    #     msg = "接口服务器异常,请联系管理员"
    elif isinstance(ex, Exception):
        logger.exception(traceback.format_exc())
        msg = str(ex)
    return ErrorResponse(msg=msg, code=code)
