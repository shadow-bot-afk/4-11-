# sw: oauthmanager.py 第三方OAuth登录管理模块
# sw: 功能：定义OAuth抽象基类，实现微博、Google、Facebook、GitHub、QQ第三方登录
# sw: 封装生成授权链接、换取access_token、获取第三方用户信息、头像解析，支持网络代理
# sw: 被oauth/views调用，读取OAuthConfig数据库配置，输出OAuthUser用户对象
import json
import logging
import os
import urllib.parse
from abc import ABCMeta, abstractmethod

import requests

from djangoblog.utils import cache_decorator
from oauth.models import OAuthUser, OAuthConfig

logger = logging.getLogger(__name__)

# sw: 自定义异常，第三方获取access_token失败时抛出
class OAuthAccessTokenException(Exception):
    '''
    oauth授权失败异常
    '''


class BaseOauthManager(metaclass=ABCMeta):
    # sw: OAuth管理器抽象基类
    # sw: 规定所有第三方登录必须实现的接口，存放公共属性，所有平台类继承此类
    """获取用户授权"""
    AUTH_URL = None # sw: 第三方授权页面地址
    """获取token"""
    TOKEN_URL = None # sw: 通过code换取access_token接口地址
    """获取用户信息"""
    API_URL = None# sw: 获取第三方用户信息接口地址
    '''icon图标名'''
    ICON_NAME = None # sw: 平台标识，和数据库配置type字段对应

    def __init__(self, access_token=None, openid=None):
        # sw: 初始化方法
        # sw: :param access_token: 第三方授权凭证
        # sw: :param openid: 第三方平台用户唯一id
        self.access_token = access_token
        self.openid = openid

    @property
    def is_access_token_set(self):
        # sw: 判断是否已经拿到access_token
        return self.access_token is not None

    @property
    def is_authorized(self):
        # sw: 判断完整授权状态：token与openid必须同时存在
        return self.is_access_token_set and self.access_token is not None and self.openid is not None

    @abstractmethod
    def get_authorization_url(self, nexturl='/'):
        # sw: 抽象方法，生成第三方登录跳转url，子类必须重写实现
        pass

    @abstractmethod
    def get_access_token_by_code(self, code):
        # sw: 抽象方法，使用回调得到的code换取access_token，子类必须重写
        pass

    @abstractmethod
    def get_oauth_userinfo(self):
        # sw: 抽象方法，请求接口拿到第三方用户资料，子类必须重写
        pass

    @abstractmethod
    def get_picture(self, metadata):
        # sw: 抽象方法，从返回数据解析用户头像地址，子类必须重写
        pass

    def do_get(self, url, params, headers=None):
        # sw: 封装通用GET网络请求方法，打印返回日志
        rsp = requests.get(url=url, params=params, headers=headers)
        logger.info(rsp.text)
        return rsp.text

    def do_post(self, url, params, headers=None):
        # sw: 封装通用POST网络请求方法，打印返回日志
        rsp = requests.post(url, params, headers=headers)
        logger.info(rsp.text)
        return rsp.text

    def get_config(self):
        # sw: 从数据库OAuthConfig表读取当前平台appkey、密钥、回调地址配置
        value = OAuthConfig.objects.filter(type=self.ICON_NAME)
        return value[0] if value else None


class WBOauthManager(BaseOauthManager):
    # sw: 微博第三方登录实现类，继承OAuth抽象基类
    AUTH_URL = 'https://api.weibo.com/oauth2/authorize'
    TOKEN_URL = 'https://api.weibo.com/oauth2/access_token'
    API_URL = 'https://api.weibo.com/2/users/show.json'
    ICON_NAME = 'weibo'

    def __init__(self, access_token=None, openid=None):
        # sw: 初始化，读取数据库微博平台的配置信息
        config = self.get_config()
        self.client_id = config.appkey if config else ''
        self.client_secret = config.appsecret if config else ''
        self.callback_url = config.callback_url if config else ''
        super(
            WBOauthManager,
            self).__init__(
            access_token=access_token,
            openid=openid)

    def get_authorization_url(self, nexturl='/'):
        # sw: 构造微博授权跳转链接，拼接回调地址与登录后跳转参数nexturl
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.callback_url + '&next_url=' + nexturl
        }
        url = self.AUTH_URL + "?" + urllib.parse.urlencode(params)
        return url

    def get_access_token_by_code(self, code):
        # sw: 使用回调得到的code，POST请求向微博接口换取access_token
        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.callback_url
        }
        rsp = self.do_post(self.TOKEN_URL, params)

        obj = json.loads(rsp)
        if 'access_token' in obj:
            self.access_token = str(obj['access_token'])
            self.openid = str(obj['uid'])
            return self.get_oauth_userinfo()
        else:
            raise OAuthAccessTokenException(rsp)

    def get_oauth_userinfo(self):
        # sw: 携带token请求微博用户信息接口，封装OAuthUser用户对象
        if not self.is_authorized:
            return None
        params = {
            'uid': self.openid,
            'access_token': self.access_token
        }
        rsp = self.do_get(self.API_URL, params)
        try:
            datas = json.loads(rsp)
            user = OAuthUser()
            user.metadata = rsp
            user.picture = datas['avatar_large']
            user.nickname = datas['screen_name']
            user.openid = datas['id']
            user.type = 'weibo'
            user.token = self.access_token
            if 'email' in datas and datas['email']:
                user.email = datas['email']
            return user
        except Exception as e:
            logger.error(e)
            logger.error('weibo oauth error.rsp:' + rsp)
            return None

    def get_picture(self, metadata):
        # sw: 从返回元数据中解析微博用户头像链接
        datas = json.loads(metadata)
        return datas['avatar_large']


class ProxyManagerMixin:
    # sw: 代理功能混入类
    # sw: 读取系统环境变量HTTP_PROXY、HTTPS_PROXY，给网络请求增加代理支持
    def __init__(self, *args, **kwargs):
        if os.environ.get("HTTP_PROXY"):
            self.proxies = {
                "http": os.environ.get("HTTP_PROXY"),
                "https": os.environ.get("HTTP_PROXY")
                # sw: 判断环境变量，组装代理字典
            }
        else:
            self.proxies = None

    def do_get(self, url, params, headers=None):
        # sw: 重写GET请求，携带代理配置访问第三方接口
        rsp = requests.get(url=url, params=params, headers=headers, proxies=self.proxies)
        logger.info(rsp.text)
        return rsp.text

    def do_post(self, url, params, headers=None):
        # sw: 重写POST请求，携带代理配置访问第三方接口
        rsp = requests.post(url, params, headers=headers, proxies=self.proxies)
        logger.info(rsp.text)
        return rsp.text


class GoogleOauthManager(ProxyManagerMixin, BaseOauthManager):
    # sw: Google平台OAuth登录实现类，继承代理混入类和抽象基类BaseOAuthManager
    AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
    TOKEN_URL = 'https://www.googleapis.com/oauth2/v4/token'
    API_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'
    ICON_NAME = 'google'

    def __init__(self, access_token=None, openid=None):
        # sw: 初始化，读取数据库Google平台配置，调用父类构造
        config = self.get_config()
        self.client_id = config.appkey if config else ''
        self.client_secret = config.appsecret if config else ''
        self.callback_url = config.callback_url if config else ''
        super(
            GoogleOauthManager,
            self).__init__(
            access_token=access_token,
            openid=openid)

    def get_authorization_url(self, nexturl='/'):
        # sw: 构造Google授权跳转链接，scope申请openid、email权限
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.callback_url,
            'scope': 'openid email',
        }
        url = self.AUTH_URL + "?" + urllib.parse.urlencode(params)
        return url

    def get_access_token_by_code(self, code):
        # sw: 使用回调code向Google接口请求access_token
        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,

            'redirect_uri': self.callback_url
        }
        rsp = self.do_post(self.TOKEN_URL, params)

        obj = json.loads(rsp)
        # sw: 判断返回结果，拿到token和openid，获取用户信息；失败抛出自定义异常
        if 'access_token' in obj:
            self.access_token = str(obj['access_token'])
            self.openid = str(obj['id_token'])
            logger.info(self.ICON_NAME + ' oauth ' + rsp)
            return self.access_token
        else:
            raise OAuthAccessTokenException(rsp)

    def get_oauth_userinfo(self):
        # sw: 携带token请求Google用户信息接口，封装OAuthUser用户对象
        if not self.is_authorized:
            return None
        params = {
            'access_token': self.access_token
        }
        rsp = self.do_get(self.API_URL, params)
        try:

            datas = json.loads(rsp)
            user = OAuthUser()
            user.metadata = rsp
            user.picture = datas['picture']
            user.nickname = datas['name']
            user.openid = datas['sub']
            user.token = self.access_token
            user.type = 'google'
            if datas['email']:
                user.email = datas['email']
            return user
        except Exception as e:
            # sw: 请求解析异常记录错误日志
            logger.error(e)
            logger.error('google oauth error.rsp:' + rsp)
            return None

    def get_picture(self, metadata):
        # sw: 从返回元数据中解析Google用户头像链接
        datas = json.loads(metadata)
        return datas['picture']


class GitHubOauthManager(ProxyManagerMixin, BaseOauthManager):
    # sw: GitHub第三方登录实现类，继承代理混入类和OAuth抽象基类
    AUTH_URL = 'https://github.com/login/oauth/authorize'
    TOKEN_URL = 'https://github.com/login/oauth/access_token'
    API_URL = 'https://api.github.com/user'
    EMAILS_API_URL = 'https://api.github.com/user/emails'
    ICON_NAME = 'github'

    def __init__(self, access_token=None, openid=None):
        # sw: 初始化，读取数据库里GitHub平台的配置信息
        config = self.get_config()
        self.client_id = config.appkey if config else ''
        self.client_secret = config.appsecret if config else ''
        self.callback_url = config.callback_url if config else ''
        super(
            GitHubOauthManager,
            self).__init__(
            access_token=access_token,
            openid=openid)

    def get_authorization_url(self, next_url='/'):
        # sw: 构造GitHub授权跳转链接，附带登录后跳转的next_url参数
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': f'{self.callback_url}&next_url={next_url}',
            'scope': 'user:email'
        }
        url = self.AUTH_URL + "?" + urllib.parse.urlencode(params)
        return url

    def get_access_token_by_code(self, code):
        # sw: 使用回调返回的code，向GitHub接口换取access_token
        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,

            'redirect_uri': self.callback_url
        }
        rsp = self.do_post(self.TOKEN_URL, params)

        from urllib import parse
        r = parse.parse_qs(rsp)
        if 'access_token' in r:
            self.access_token = (r['access_token'][0])
            return self.access_token
        else:
            raise OAuthAccessTokenException(rsp)

    def get_oauth_userinfo(self):
        # sw: 携带token请求用户信息接口，拿用户昵称、头像、邮箱，封装OAuthUser对象
        rsp = self.do_get(self.API_URL, params={}, headers={
            "Authorization": "Bearer " + self.access_token
        })
        try:
            datas = json.loads(rsp)
            user = OAuthUser()
            user.picture = datas['avatar_url']
            user.nickname = datas['name']
            user.openid = datas['id']
            user.type = 'github'
            user.token = self.access_token
            user.metadata = rsp
            if 'email' in datas and datas['email']:
                user.email = datas['email']
            else:
                # sw: 基础接口拿不到邮箱时，单独调用邮箱接口获取验证过的邮箱
                # If email is not public, fetch from /user/emails endpoint
                try:
                    emails_rsp = self.do_get(self.EMAILS_API_URL, params={}, headers={
                        "Authorization": "Bearer " + self.access_token
                    })
                    emails = json.loads(emails_rsp)
                    # Find verified email, prioritizing primary verified email
                    for email_data in emails:
                        if email_data.get('verified'):
                            if email_data.get('primary'):
                                # Primary verified email takes priority
                                user.email = email_data.get('email')
                                break
                            elif not user.email:
                                # Use first verified email as fallback
                                user.email = email_data.get('email')
                except Exception as e:
                    logger.warning(f'Failed to fetch private email from GitHub API. User login will fail if email is required: {e}')
            return user
        except Exception as e:
            logger.error(e)
            logger.error('github oauth error.rsp:' + rsp)
            return None

    def get_picture(self, metadata):
        # sw: 从返回的元数据json中解析头像链接
        datas = json.loads(metadata)
        return datas['avatar_url']


class FaceBookOauthManager(ProxyManagerMixin, BaseOauthManager):
    # sw: Facebook第三方登录实现类，继承代理混入类和OAuth抽象基类
    AUTH_URL = 'https://www.facebook.com/v16.0/dialog/oauth'
    TOKEN_URL = 'https://graph.facebook.com/v16.0/oauth/access_token'
    API_URL = 'https://graph.facebook.com/me'
    ICON_NAME = 'facebook'

    def __init__(self, access_token=None, openid=None):
        # sw: 初始化，读取数据库Facebook平台的配置信息
        config = self.get_config()
        self.client_id = config.appkey if config else ''
        self.client_secret = config.appsecret if config else ''
        self.callback_url = config.callback_url if config else ''
        super(
            FaceBookOauthManager,
            self).__init__(
            access_token=access_token,
            openid=openid)

    def get_authorization_url(self, next_url='/'):
        # sw: 构造Facebook授权跳转链接，申请邮箱和公开资料权限
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.callback_url,
            'scope': 'email,public_profile'
        }
        url = self.AUTH_URL + "?" + urllib.parse.urlencode(params)
        return url

    def get_access_token_by_code(self, code):
        # sw: 使用回调返回的code向Facebook接口换取access_token
        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            # 'grant_type': 'authorization_code',
            'code': code,

            'redirect_uri': self.callback_url
        }
        rsp = self.do_post(self.TOKEN_URL, params)

        obj = json.loads(rsp)
        if 'access_token' in obj:
            token = str(obj['access_token'])
            self.access_token = token
            return self.access_token
        else:
            raise OAuthAccessTokenException(rsp)

    def get_oauth_userinfo(self):
        # sw: 携带token请求用户信息接口，获取昵称、头像、邮箱，封装OAuthUser对象
        params = {
            'access_token': self.access_token,
            'fields': 'id,name,picture,email'
        }
        try:
            rsp = self.do_get(self.API_URL, params)
            datas = json.loads(rsp)
            user = OAuthUser()
            user.nickname = datas['name']
            user.openid = datas['id']
            user.type = 'facebook'
            user.token = self.access_token
            user.metadata = rsp
            if 'email' in datas and datas['email']:
                user.email = datas['email']
            if 'picture' in datas and datas['picture'] and datas['picture']['data'] and datas['picture']['data']['url']:
                user.picture = str(datas['picture']['data']['url'])
            return user
        except Exception as e:
            logger.error(e)
            return None

    def get_picture(self, metadata):
        # sw: 从返回的元数据json中解析头像链接
        datas = json.loads(metadata)
        return str(datas['picture']['data']['url'])


class QQOauthManager(BaseOauthManager):
    # sw: QQ第三方登录实现类，继承OAuth抽象基类
    AUTH_URL = 'https://graph.qq.com/oauth2.0/authorize'
    TOKEN_URL = 'https://graph.qq.com/oauth2.0/token'
    API_URL = 'https://graph.qq.com/user/get_user_info'
    OPEN_ID_URL = 'https://graph.qq.com/oauth2.0/me'
    ICON_NAME = 'qq'

    def __init__(self, access_token=None, openid=None):
        # sw: 初始化，读取数据库QQ平台的配置信息
        config = self.get_config()
        self.client_id = config.appkey if config else ''
        self.client_secret = config.appsecret if config else ''
        self.callback_url = config.callback_url if config else ''
        super(
            QQOauthManager,
            self).__init__(
            access_token=access_token,
            openid=openid)

    def get_authorization_url(self, next_url='/'):
        # sw: 构造QQ授权跳转链接，拼接回调地址与登录后跳转参数next_url
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.callback_url + '&next_url=' + next_url,
        }
        url = self.AUTH_URL + "?" + urllib.parse.urlencode(params)
        return url

    def get_access_token_by_code(self, code):
        # sw: 使用回调得到的code，调用接口GET请求换取access_token
        params = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.callback_url
        }
        rsp = self.do_get(self.TOKEN_URL, params)
        if rsp:
            d = urllib.parse.parse_qs(rsp)
            if 'access_token' in d:
                token = d['access_token']
                self.access_token = token[0]
                return token
        else:
            raise OAuthAccessTokenException(rsp)

    def get_open_id(self):
        if self.is_access_token_set:
            params = {
                'access_token': self.access_token
            }
            rsp = self.do_get(self.OPEN_ID_URL, params)
            if rsp:
                rsp = rsp.replace(
                    'callback(', '').replace(
                    ')', '').replace(
                    ';', '')
                obj = json.loads(rsp)
                openid = str(obj['openid'])
                self.openid = openid
                return openid

    def get_oauth_userinfo(self):
        # sw: 先获取QQ的openid，再请求用户信息接口，封装OAuthUser用户对象
        openid = self.get_open_id()
        if openid:
            params = {
                'access_token': self.access_token,
                'oauth_consumer_key': self.client_id,
                'openid': self.openid
            }
            rsp = self.do_get(self.API_URL, params)
            logger.info(rsp)
            obj = json.loads(rsp)
            user = OAuthUser()
            user.nickname = obj['nickname']
            user.openid = openid
            user.type = 'qq'
            user.token = self.access_token
            user.metadata = rsp
            if 'email' in obj:
                user.email = obj['email']
            if 'figureurl' in obj:
                user.picture = str(obj['figureurl'])
            return user

    def get_picture(self, metadata):
        # sw: 从返回元数据中解析QQ用户头像链接
        datas = json.loads(metadata)
        return str(datas['figureurl'])


@cache_decorator(expiration=100 * 60)
def get_oauth_apps():
    # sw: 获取所有已经启用的第三方OAuth应用，使用缓存装饰器提升性能
    configs = OAuthConfig.objects.filter(is_enable=True).all()
    if not configs:
        return []
    configtypes = [x.type for x in configs]
    applications = BaseOauthManager.__subclasses__()
    apps = [x() for x in applications if x().ICON_NAME.lower() in configtypes]
    return apps


def get_manager_by_type(type):
    # sw: 根据传入的类型名称，找到对应的OAuth管理类并返回
    applications = get_oauth_apps()
    if applications:
        finds = list(
            filter(
                lambda x: x.ICON_NAME.lower() == type.lower(),
                applications))
        if finds:
            return finds[0]
    return None
