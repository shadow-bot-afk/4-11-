# zzy: 模块功能：微信公众号机器人核心，基于WeRoBot实现——
# 支持关键词搜索文章、分类/最新文章浏览、管理员验证后执行服务器命令、
# 默认对接ChatGPT对话；会话优先存缓存、降级存本地文件
import logging
import os
import re

import jsonpickle
from django.conf import settings
from werobot import WeRoBot
from werobot.replies import ArticlesReply, Article
from werobot.session.filestorage import FileStorage

from djangoblog.utils import get_sha256
from servermanager.api.blogapi import BlogApi
from servermanager.api.commonapi import ChatGPT, CommandHandler
from .MemcacheStorage import MemcacheStorage

# zzy: 机器人初始化：token从环境变量读取(默认值为项目原作者标识)；
# 会话存储按缓存可用性选择后端；blogapi提供文章查询，cmd_handler提供命令执行
robot = WeRoBot(token=os.environ.get('DJANGO_WEROBOT_TOKEN')
                      or 'lylinux', enable_session=True)
memstorage = MemcacheStorage()
if memstorage.is_available:
    robot.config['SESSION_STORAGE'] = memstorage
else:
    if os.path.exists(os.path.join(settings.BASE_DIR, 'werobot_session')):
        os.remove(os.path.join(settings.BASE_DIR, 'werobot_session'))
    robot.config['SESSION_STORAGE'] = FileStorage(filename='werobot_session')

blogapi = BlogApi()
cmd_handler = CommandHandler()
logger = logging.getLogger(__name__)


def convert_to_article_reply(articles, message):
    reply = ArticlesReply(message=message)
    from blog.templatetags.blog_tags import truncatechars_content
    for post in articles:
        imgs = re.findall(r'(?:http\:|https\:)?\/\/.*\.(?:png|jpg)', post.body)
        imgurl = ''
        if imgs:
            imgurl = imgs[0]
        article = Article(
            title=post.title,
            description=truncatechars_content(post.body),
            img=imgurl,
            url=post.get_full_url()
        )
        reply.add_article(article)
    return reply

# zzy: 指令处理：用户发送?+关键词时搜索文章，有结果返回图文列表，否则提示未找到
@robot.filter(re.compile(r"^\?.*"))
def search(message, session):
    s = message.content
    searchstr = str(s).replace('?', '')
    result = blogapi.search_articles(searchstr)
    if result:
        articles = list(map(lambda x: x.object, result))
        reply = convert_to_article_reply(articles, message)
        return reply
    else:
        return '没有找到相关文章。'

# zzy: 指令处理：返回所有文章分类名列表
@robot.filter(re.compile(r'^category\s*$', re.I))
def category(message, session):
    categorys = blogapi.get_category_lists()
    content = ','.join(map(lambda x: x.name, categorys))
    return '所有文章分类目录：' + content

# zzy: 指令处理：返回最新文章图文列表
@robot.filter(re.compile(r'^recent\s*$', re.I))
def recents(message, session):
    articles = blogapi.get_recent_articles()
    if articles:
        reply = convert_to_article_reply(articles, message)
        return reply
    else:
        return "暂时还没有文章"

# zzy: 指令处理：返回机器人使用帮助说明
@robot.filter(re.compile('^help$', re.I))
def help(message, session):
    return '''欢迎关注!
            默认会与图灵机器人聊天~~
        你可以通过下面这些命令来获得信息
        ?关键字搜索文章.
        如?python.
        category获得文章分类目录及文章数.
        category-***获得该分类目录文章
        如category-python
        recent获得最新文章
        help获得帮助.
        weather:获得天气
        如weather:西安
        idcard:获得身份证信息
        如idcard:61048119xxxxxxxxxx
        music:音乐搜索
        如music:阴天快乐
        PS:以上标点符号都不支持中文标点~~
        '''

# zzy: 指令处理：天气查询(功能未实现，占位返回建设中)
@robot.filter(re.compile(r'^weather\:.*$', re.I))
def weather(message, session):
    return "建设中..."

# zzy: 指令处理：身份证信息查询(功能未实现，占位返回建设中)
@robot.filter(re.compile(r'^idcard\:.*$', re.I))
def idcard(message, session):
    return "建设中..."

# zzy: 兜底处理器：未命中任何指令的消息走MessageHandler，按用户状态分流处理
@robot.handler
def echo(message, session):
    handler = MessageHandler(message, session)
    return handler.handler()

# zzy: 消息处理器：管理微信用户会话状态(普通/待验证管理员/已验证管理员)，
# 处理管理员密码校验(限3次)、命令确认执行，普通用户消息转交ChatGPT回复
class MessageHandler:
    def __init__(self, message, session):
        userid = message.source
        self.message = message
        self.session = session
        self.userid = userid
        try:
            info = session[userid]
            self.userinfo = jsonpickle.decode(info)
        except Exception:
            userinfo = WxUserInfo()
            self.userinfo = userinfo

    @property
    def is_admin(self):
        return self.userinfo.isAdmin

    @property
    def is_password_set(self):
        return self.userinfo.isPasswordSet

    def save_session(self):
        info = jsonpickle.encode(self.userinfo)
        self.session[self.userid] = info
# zzy: 核心分流逻辑：按用户状态依次判断——退出指令重置状态、ADMIN进入验证、
# 密码校验、命令确认(Y执行/其他暂存待确认)，均不满足则交ChatGPT
    def handler(self):
        info = self.message.content

        if self.userinfo.isAdmin and info.upper() == 'EXIT':
            self.userinfo = WxUserInfo()
            self.save_session()
            return "退出成功"
        if info.upper() == 'ADMIN':
            self.userinfo.isAdmin = True
            self.save_session()
            return "输入管理员密码"
        if self.userinfo.isAdmin and not self.userinfo.isPasswordSet:
            passwd = settings.WXADMIN
            if settings.TESTING:
                passwd = '123'
            if passwd.upper() == get_sha256(get_sha256(info)).upper():
                self.userinfo.isPasswordSet = True
                self.save_session()
                return "验证通过,请输入命令或者要执行的命令代码:输入helpme获得帮助"
            else:
                if self.userinfo.Count >= 3:
                    self.userinfo = WxUserInfo()
                    self.save_session()
                    return "超过验证次数"
                self.userinfo.Count += 1
                self.save_session()
                return "验证失败，请重新输入管理员密码:"
        if self.userinfo.isAdmin and self.userinfo.isPasswordSet:
            if self.userinfo.Command != '' and info.upper() == 'Y':
                return cmd_handler.run(self.userinfo.Command)
            else:
                if info.upper() == 'HELPME':
                    return cmd_handler.get_help()
                self.userinfo.Command = info
                self.save_session()
                return "确认执行: " + info + " 命令?"

        return ChatGPT.chat(info)

# zzy: 微信用户会话状态对象：记录是否申请管理员、是否已通过密码验证、
# 验证失败次数与待执行命令，经jsonpickle序列化后存入会话
class WxUserInfo():
    def __init__(self):
        self.isAdmin = False
        self.isPasswordSet = False
        self.Count = 0
        self.Command = ''
