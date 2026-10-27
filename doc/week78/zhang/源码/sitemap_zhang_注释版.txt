# zhang: 模块职责：定义文章、分类、标签、用户及静态页面的站点地图。
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from blog.models import Article, Category, Tag


# zhang: 类职责：收集静态页面的站点地图地址。
class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'daily'

    # zhang: 方法职责：获取站点地图或订阅记录。
    def items(self):
        return ['blog:index', ]

    # zhang: 方法职责：生成站点地图条目地址。
    def location(self, item):
        return reverse(item)


# zhang: 类职责：收集文章的站点地图地址。
class ArticleSiteMap(Sitemap):
    changefreq = "monthly"
    priority = "0.6"

    # zhang: 方法职责：获取站点地图或订阅记录。
    def items(self):
        return Article.objects.filter(status='p')

    # zhang: 方法职责：获取站点地图条目修改时间。
    def lastmod(self, obj):
        return obj.last_modify_time


# zhang: 类职责：收集分类的站点地图地址。
class CategorySiteMap(Sitemap):
    changefreq = "Weekly"
    priority = "0.6"

    # zhang: 方法职责：获取站点地图或订阅记录。
    def items(self):
        return Category.objects.all()

    # zhang: 方法职责：获取站点地图条目修改时间。
    def lastmod(self, obj):
        return obj.last_modify_time


# zhang: 类职责：收集标签的站点地图地址。
class TagSiteMap(Sitemap):
    changefreq = "Weekly"
    priority = "0.3"

    # zhang: 方法职责：获取站点地图或订阅记录。
    def items(self):
        return Tag.objects.all()

    # zhang: 方法职责：获取站点地图条目修改时间。
    def lastmod(self, obj):
        return obj.last_modify_time


# zhang: 类职责：收集用户相关的站点地图地址。
class UserSiteMap(Sitemap):
    changefreq = "Weekly"
    priority = "0.3"

    # zhang: 方法职责：获取站点地图或订阅记录。
    def items(self):
        return list(set(map(lambda x: x.author, Article.objects.all())))

    # zhang: 方法职责：获取站点地图条目修改时间。
    def lastmod(self, obj):
        return obj.date_joined
