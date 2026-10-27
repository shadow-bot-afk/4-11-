# zzy: 模块功能：为微信机器人提供基于Django缓存的会话存储实现，
# 缓存不可用时由robot.py降级为文件存储
from werobot.session import SessionStorage
from werobot.utils import json_loads, json_dumps

from djangoblog.utils import cache

# zzy: 会话存储类：继承werobot的SessionStorage，用Django cache读写会话数据，
# 键名统一加前缀ws_防止冲突
class MemcacheStorage(SessionStorage):
    def __init__(self, prefix='ws_'):
        self.prefix = prefix
        self.cache = cache

    @property
    # zzy: 检测缓存是否可用：写入测试键再读取比对，成功说明缓存服务正常
    def is_available(self):
        value = "1"
        self.set('checkavaliable', value=value)
        return value == self.get('checkavaliable')

    def key_name(self, s):
        return '{prefix}{s}'.format(prefix=self.prefix, s=s)
# zzy: 读取会话：从缓存取出JSON字符串并解析，无数据时返回空字典
    def get(self, id):
        id = self.key_name(id)
        session_json = self.cache.get(id) or '{}'
        return json_loads(session_json)
# zzy: 保存会话：将会话对象序列化为JSON写入缓存
    def set(self, id, value):
        id = self.key_name(id)
        self.cache.set(id, json_dumps(value))
# zzy: 删除指定会话
    def delete(self, id):
        id = self.key_name(id)
        self.cache.delete(id)
