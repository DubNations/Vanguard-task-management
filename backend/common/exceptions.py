import logging

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """统一错误响应格式。"""
    response = exception_handler(exc, context)

    if response is not None:
        data = {
            'error': {
                'code': response.status_code,
                'message': _extract_message(response.data),
                'detail': response.data if isinstance(response.data, dict) else None,
            }
        }
        response.data = data
        return response

    # Unhandled exception
    logger.exception('Unhandled exception in view: %s', exc)
    return Response(
        {
            'error': {
                'code': 500,
                'message': '服务器内部错误，请稍后重试',
                'detail': None,
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _extract_message(data):
    if isinstance(data, dict):
        if 'detail' in data:
            return str(data['detail'])
        if 'non_field_errors' in data:
            return str(data['non_field_errors'][0])
        for key, value in data.items():
            if isinstance(value, list) and value:
                return f'{key}: {value[0]}'
    if isinstance(data, list) and data:
        return str(data[0])
    return str(data)
