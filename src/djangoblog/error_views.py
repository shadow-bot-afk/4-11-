#!/usr/bin/env python
# encoding: utf-8

"""
Django Blog 统一错误处理视图
提供统一的错误页面渲染，减少重复代码
"""

import logging
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

# zhang: 使用模块级日志记录器，统一记录错误处理时的异常信息。
logger = logging.getLogger(__name__)


# zhang: 统一渲染错误页，避免各HTTP错误处理函数重复构造响应。
def render_error_page(request, status_code, message, exception=None):
    """
    通用错误页面渲染函数

    统一处理各种 HTTP 错误，提供一致的错误页面展示

    Args:
        request: HTTP 请求对象
        status_code: HTTP 状态码（404, 403, 500等）
        message: 错误消息（支持国际化）
        exception: 异常对象（可选），会被记录到日志

    Returns:
        HttpResponse: 渲染后的错误页面

    Usage:
        def my_error_handler(request, exception):
            return render_error_page(request, 404, "Page not found", exception)
    """
    # zhang: 仅在提供异常对象时记录诊断信息，保持无异常场景的处理逻辑不变。
    if exception:
        logger.error(
            f'HTTP {status_code} Error: {exception}',
            exc_info=True,
            extra={
                'request': request,
                'status_code': status_code
            }
        )

    # zhang: 共用错误页模板，并使用实际HTTP状态码返回响应。
    return render(
        request,
        'blog/error_page.html',
        {
            'message': message,
            'statuscode': str(status_code)
        },
        status=status_code
    )


# zhang: 将404错误交由通用渲染函数处理。
def page_not_found_view(request, exception, template_name='blog/error_page.html'):
    """
    404 错误页面处理器

    当用户访问不存在的页面时显示

    Args:
        request: HTTP 请求对象
        exception: 异常对象
        template_name: 模板名称（保留参数以兼容 Django 标准）

    Returns:
        HttpResponse: 404 错误页面
    """
    return render_error_page(
        request,
        404,
        _('Sorry, the page you requested is not found, please click the home page to see other?'),
        exception
    )


# zhang: 500错误处理器不要求接收异常参数。
def server_error_view(request, template_name='blog/error_page.html'):
    """
    500 错误页面处理器

    当服务器内部错误时显示

    Args:
        request: HTTP 请求对象
        template_name: 模板名称（保留参数以兼容 Django 标准）

    Returns:
        HttpResponse: 500 错误页面
    """
    return render_error_page(
        request,
        500,
        _('Sorry, the server is busy, please click the home page to see other?')
    )


# zhang: 403错误显示权限不足提示，并传递异常供日志记录。
def permission_denied_view(request, exception, template_name='blog/error_page.html'):
    """
    403 错误页面处理器

    当用户无权限访问时显示

    Args:
        request: HTTP 请求对象
        exception: 异常对象
        template_name: 模板名称（保留参数以兼容 Django 标准）

    Returns:
        HttpResponse: 403 错误页面
    """
    return render_error_page(
        request,
        403,
        _('Sorry, you do not have permission to access this page?'),
        exception
    )


# zhang: 400错误显示无效请求提示，并传递异常供日志记录。
def bad_request_view(request, exception, template_name='blog/error_page.html'):
    """
    400 错误页面处理器

    当请求格式错误时显示

    Args:
        request: HTTP 请求对象
        exception: 异常对象
        template_name: 模板名称（保留参数以兼容 Django 标准）

    Returns:
        HttpResponse: 400 错误页面
    """
    return render_error_page(
        request,
        400,
        _('Sorry, the request was invalid?'),
        exception
    )
