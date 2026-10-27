# zhang: 模块职责：DjangoBlog 应用的基础测试入口。
from django.test import TestCase

from djangoblog.utils import *


# zhang: 类职责：组织 DjangoBlogTest 相关功能与状态。
class DjangoBlogTest(TestCase):
    # zhang: 方法职责：准备测试数据与依赖。
    def setUp(self):
        pass

    # zhang: 方法职责：测试 utils 场景的预期行为。
    def test_utils(self):
        md5 = get_sha256('test')
        self.assertIsNotNone(md5)
        c = CommonMarkdown.get_markdown('''
        # Title1

        ```python
        import os
        ```

        [url](https://www.lylinux.net/)

        [ddd](http://www.baidu.com)


        ''')
        self.assertIsNotNone(c)
        d = {
            'd': 'key1',
            'd2': 'key2'
        }
        data = parse_dict_to_url(d)
        self.assertIsNotNone(data)
