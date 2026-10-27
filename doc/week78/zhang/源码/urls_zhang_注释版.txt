"""djangoblog URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
# zhang: 导入项目配置及路由相关组件，集中管理博客的全局URL入口。
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.urls import re_path
from haystack.views import search_view_factory
from django.http import JsonResponse
import time

# zhang: 引入各业务模块的视图、管理后台、搜索表单、订阅和站点地图组件。
from blog.views import EsSearchView
from djangoblog.admin_site import admin_site
from djangoblog.elasticsearch_backend import ElasticSearchModelSearchForm
from djangoblog.feeds import DjangoBlogFeed
from djangoblog.sitemap import ArticleSiteMap, CategorySiteMap, StaticViewSitemap, TagSiteMap, UserSiteMap

# zhang: 汇总文章、分类、标签、用户和静态页面站点地图，供搜索引擎索引。
sitemaps = {

    'blog': ArticleSiteMap,
    'Category': CategorySiteMap,
    'Tag': TagSiteMap,
    'User': UserSiteMap,
    'static': StaticViewSitemap
}

# zhang: 注册全局错误处理视图；以下名称沿用项目现有配置。
handler404 = 'blog.views.page_not_found_view'
handler500 = 'blog.views.server_error_view'
handle403 = 'blog.views.permission_denied_view'


# zhang: 定义不依赖数据库查询的轻量级健康检查接口。
def health_check(request):
    """
    健康检查接口
    简单返回服务健康状态
    """
    # zhang: 返回服务状态及当前时间戳，供状态检查使用。
    return JsonResponse({
        'status': 'healthy',
        'timestamp': time.time()
    })

# zhang: 注册语言切换和健康检查等不需要多语言前缀的路由。
urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('health/', health_check, name='health_check'),
]
# zhang: 将后台、文章、评论、账户、第三方登录和管理功能接入多语言路由。
# zhang: 保留原有顺序，避免通用匹配规则影响既有URL解析。
urlpatterns += i18n_patterns(
    re_path(r'^admin/', admin_site.urls),
    re_path(r'', include('blog.urls', namespace='blog')),
    re_path(r'mdeditor/', include('mdeditor.urls')),
    re_path(r'', include('comments.urls', namespace='comment')),
    re_path(r'', include('accounts.urls', namespace='account')),
    re_path(r'', include('oauth.urls', namespace='oauth')),
    # zhang: 提供网站地图接口，便于搜索引擎发现公开页面。
    re_path(r'^sitemap\.xml$', sitemap, {'sitemaps': sitemaps},
            name='django.contrib.sitemaps.views.sitemap'),
    # zhang: 将 feed 与 rss 路径映射至文章订阅输出。
    re_path(r'^feed/$', DjangoBlogFeed()),
    re_path(r'^rss/$', DjangoBlogFeed()),
    # zhang: 使用项目自定义搜索视图及搜索表单处理查询请求。
    re_path('^search', search_view_factory(view_class=EsSearchView, form_class=ElasticSearchModelSearchForm),
            name='search'),
    re_path(r'', include('servermanager.urls', namespace='servermanager'))
    , prefix_default_language=False) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
# zhang: 仅在调试模式下由Django提供媒体文件访问路由；生产环境应交由静态资源服务处理。
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
