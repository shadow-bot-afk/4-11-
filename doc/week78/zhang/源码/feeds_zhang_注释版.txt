# zhang: 模块职责：定义博客文章的 RSS/Atom 订阅内容。
from django.contrib.auth import get_user_model
from django.contrib.syndication.views import Feed
from django.utils import timezone
from django.utils.feedgenerator import Rss201rev2Feed

from blog.models import Article
from djangoblog.utils import CommonMarkdown


# zhang: 类职责：向订阅客户端输出博客内容。
class DjangoBlogFeed(Feed):
    feed_type = Rss201rev2Feed

    description = '大巧无工,重剑无锋.'
    title = "且听风吟 大巧无工,重剑无锋. "
    link = "/feed/"

    # zhang: 方法职责：封装 author name 对应的处理步骤。
    def author_name(self):
        return get_user_model().objects.first().nickname

    # zhang: 方法职责：封装 author link 对应的处理步骤。
    def author_link(self):
        return get_user_model().objects.first().get_absolute_url()

    # zhang: 方法职责：获取站点地图或订阅记录。
    def items(self):
        return Article.objects.filter(type='a', status='p').order_by('-pub_time')[:5]

    # zhang: 方法职责：生成订阅条目标题。
    def item_title(self, item):
        return item.title

    # zhang: 方法职责：生成订阅条目摘要。
    def item_description(self, item):
        return CommonMarkdown.get_markdown(item.body)

    # zhang: 方法职责：封装 feed copyright 对应的处理步骤。
    def feed_copyright(self):
        now = timezone.now()
        return "Copyright© {year} 且听风吟".format(year=now.year)

    # zhang: 方法职责：生成订阅条目链接。
    def item_link(self, item):
        return item.get_absolute_url()

    # zhang: 方法职责：封装 item guid 对应的处理步骤。
    def item_guid(self, item):
        return
