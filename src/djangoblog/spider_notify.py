# zhang: 模块职责：向搜索引擎提交需要收录的网址。
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


# zhang: 类职责：统一搜索引擎通知入口。
class SpiderNotify():
    # zhang: 方法职责：封装 baidu notify 对应的处理步骤。
    @staticmethod
    def baidu_notify(urls):
        try:
            data = '\n'.join(urls)
            result = requests.post(settings.BAIDU_NOTIFY_URL, data=data)
            logger.info(result.text)
        except Exception as e:
            logger.error(e)

    # zhang: 方法职责：封装 notify 对应的处理步骤。
    @staticmethod
    def notify(url):
        SpiderNotify.baidu_notify(url)
