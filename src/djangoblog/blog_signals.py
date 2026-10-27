# zhang: 本模块集中处理邮件发送、OAuth 登录、模型保存和用户认证等 Django 信号。
import _thread
import logging

import django.dispatch
from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_save
from django.dispatch import receiver

from comments.models import Comment
from comments.utils import send_comment_email
from djangoblog.spider_notify import SpiderNotify
from djangoblog.utils import cache, expire_view_cache, delete_sidebar_cache, delete_view_cache
from djangoblog.utils import get_current_site
from oauth.models import OAuthUser

logger = logging.getLogger(__name__)

# zhang: 定义 OAuth 登录及异步邮件请求使用的自定义信号。
oauth_user_login_signal = django.dispatch.Signal(['id'])
send_email_signal = django.dispatch.Signal(
    ['emailto', 'title', 'content'])


# zhang: 接收到邮件信号后发送 HTML 邮件，并记录实际发送结果。
@receiver(send_email_signal)
def send_email_signal_handler(sender, **kwargs):
    emailto = kwargs['emailto']
    title = kwargs['title']
    content = kwargs['content']

    # zhang: 根据信号参数构造邮件消息，发件地址使用项目配置。
    msg = EmailMultiAlternatives(
        title,
        content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=emailto)
    msg.content_subtype = "html"

    from servermanager.models import EmailSendLog
    log = EmailSendLog()
    log.title = title
    log.content = content
    log.emailto = ','.join(emailto)

    # zhang: 即使发送失败也保存邮件日志，便于排查邮件服务问题。
    try:
        result = msg.send()
        log.send_result = result > 0
    except Exception as e:
        logger.error(f"失败邮箱号: {emailto}, {e}")
        log.send_result = False
    log.save()


# zhang: OAuth 登录后按需保存远程头像，并清除侧边栏缓存。
@receiver(oauth_user_login_signal)
def oauth_user_login_signal_handler(sender, **kwargs):
    id = kwargs['id']
    oauthuser = OAuthUser.objects.get(id=id)
    site = get_current_site().domain
    # zhang: 只有头像地址未包含站点域名时才尝试保存为本地头像。
    if oauthuser.picture and not oauthuser.picture.find(site) >= 0:
        from djangoblog.utils import save_user_avatar
        oauthuser.picture = save_user_avatar(oauthuser.picture)
        oauthuser.save()

    delete_sidebar_cache()


# zhang: 监听模型保存事件，负责搜索通知及与文章、评论相关的缓存失效。
@receiver(post_save)
def model_post_save_callback(
        sender,
        instance,
        created,
        raw,
        using,
        update_fields,
        **kwargs):
    # zhang: 跳过后台操作日志，避免无关模型更新触发缓存清理。
    if isinstance(instance, LogEntry):
        return

    # 检查是否只更新了浏览量
    # zhang: 单独更新浏览量时不清理文章缓存，降低频繁写入带来的开销。
    is_update_views = update_fields == {'views'}
    if is_update_views:
        return  # 浏览量更新不需要清理缓存

    # 搜索引擎通知
    # zhang: 为具有公开地址的模型尝试通知搜索引擎，测试环境不执行该请求。
    if 'get_full_url' in dir(instance):
        if not settings.TESTING:
            try:
                notify_url = instance.get_full_url()
                SpiderNotify.baidu_notify([notify_url])
            except Exception as ex:
                logger.error("notify sipder", ex)

    # 评论相关的缓存清理
    # zhang: 已启用评论更新后失效详情页和侧边栏缓存，并触发通知邮件。
    if isinstance(instance, Comment):
        if instance.is_enable:
            path = instance.article.get_absolute_url()
            site = get_current_site().domain
            if site.find(':') > 0:
                site = site[0:site.find(':')]

            expire_view_cache(
                path,
                servername=site,
                serverport=80,
                key_prefix='blogdetail')

            # 清理评论相关缓存
            comment_cache_key = 'article_comments_{id}'.format(
                id=instance.article.id)
            cache.delete(comment_cache_key)
            delete_view_cache('article_comments', [str(instance.article.pk)])
            delete_sidebar_cache()
            cache.delete('seo_processor')

            # zhang: 邮件通知通过底层线程启动；发送失败的处理需另外核查。
            _thread.start_new_thread(send_comment_email, (instance,))

    # 文章相关的精细化缓存清理
    elif 'get_full_url' in dir(instance):
        from blog.models import Article, Category, Tag

        # zhang: 文章保存后分别清理列表、详情、分类、标签及作者缓存。
        if isinstance(instance, Article):
            # 清理文章列表首页缓存
            cache.delete('index_1')

            # 清理文章详情缓存
            article_cache_key = f'article_comments_{instance.id}'
            cache.delete(article_cache_key)

            # 清理分类相关缓存
            if instance.category:
                category_name = instance.category.name
                cache.delete(f'category_list_{category_name}_1')

            # 清理标签相关缓存
            try:
                for tag in instance.tags.all():
                    cache.delete(f'tag_{tag.name}_1')
            except Exception:
                pass  # 可能在创建时tags还未关联

            # 清理作者相关缓存
            if instance.author:
                from uuslug import slugify
                author_slug = slugify(instance.author.username)
                cache.delete(f'author_{author_slug}_1')

            # 清理归档缓存
            cache.delete('archives')

            # 清理侧边栏和上下文处理器缓存
            delete_sidebar_cache()
            cache.delete('seo_processor')

        # zhang: 分类变化时清理对应列表及全站相关缓存。
        elif isinstance(instance, Category):
            # 清理分类相关缓存
            cache.delete(f'category_list_{instance.name}_1')
            delete_sidebar_cache()
            cache.delete('seo_processor')

        # zhang: 标签变化时清理标签页缓存和侧边栏缓存。
        elif isinstance(instance, Tag):
            # 清理标签相关缓存
            cache.delete(f'tag_{instance.name}_1')
            delete_sidebar_cache()

        # 其他模型的缓存清理
        else:
            # 对于其他有get_full_url的模型，清理基础缓存
            delete_sidebar_cache()
            cache.delete('seo_processor')


# zhang: 用户登录或登出时清理侧边栏缓存，避免展示过期用户状态。
@receiver(user_logged_in)
@receiver(user_logged_out)
def user_auth_callback(sender, request, user, **kwargs):
    if user and user.username:
        logger.info(user)
        delete_sidebar_cache()
        # cache.clear()
