import os

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.paginator import Paginator
from django.templatetags.static import static
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import BlogUser
from blog.forms import BlogSearchForm
from blog.models import Article, Category, Tag, SideBar, Links
from blog.templatetags.blog_tags import load_pagination_info, load_articletags, highlight_search_term, highlight_content
from djangoblog.utils import get_current_site, get_sha256
from oauth.models import OAuthUser, OAuthConfig


# Create your tests here.

# GJ: 文章模块单元测试类，用于验证文章相关视图和后台功能是否正常。
class ArticleTest(TestCase):
    # GJ: 测试初始化方法：每次执行测试前，实例化测试客户端和请求工厂。
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

    # GJ: 核心测试用例：模拟创建超级管理员用户，并测试后台页面和侧边栏的访问状态。
    def test_validate_article(self):
        site = get_current_site().domain
        user = BlogUser.objects.get_or_create(
            email="liangliangyy@gmail.com",
            username="liangliangyy")[0]
        user.set_password("liangliangyy")
        user.is_staff = True
        user.is_superuser = True
        user.save()
        response = self.client.get(user.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/admin/servermanager/emailsendlog/')
        response = self.client.get('admin/admin/logentry/')
        s = SideBar()
        s.sequence = 1
        s.name = 'test'
        s.content = 'test content'
        s.is_enable = True
        s.save()

        category = Category()
        category.name = "category"
        category.creation_time = timezone.now()
        category.last_mod_time = timezone.now()
        category.save()

        tag = Tag()
        tag.name = "nicetag"
        tag.save()

        article = Article()
        article.title = "nicetitle"
        article.body = "nicecontent"
        article.author = user
        article.category = category
        article.type = 'a'
        article.status = 'p'

        article.save()
        # GJ: 断言新建文章时，关联的标签数量初始为0
        self.assertEqual(0, article.tags.count())
        article.tags.add(tag)
        article.save()
        # GJ: 断言在添加一个标签并保存后，文章的关联标签数量变为1
        self.assertEqual(1, article.tags.count())
        # GJ: 循环批量创建20篇文章，用于测试分页功能或列表页的数据渲染性能
        for i in range(20):
            article = Article()
            article.title = "nicetitle" + str(i)
            article.body = "nicetitle" + str(i)
            article.author = user
            article.category = category
            article.type = 'a'
            article.status = 'p'
            article.save()
            article.tags.add(tag)
            article.save()
        from blog.documents import ELASTICSEARCH_ENABLED
        # GJ: 若开启了搜索引擎，则构建索引并测试搜索接口的响应状态
        if ELASTICSEARCH_ENABLED:
            call_command("build_index")
            response = self.client.get('/search', {'q': 'nicetitle'})
            self.assertEqual(response.status_code, 200)
        # GJ: 测试文章、标签、分类详情页的访问，并断言均返回 200 状态码
        response = self.client.get(article.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        from djangoblog.spider_notify import SpiderNotify
        # GJ: 模拟向蜘蛛池提交文章链接，用于搜索引擎收录测试
        SpiderNotify.notify(article.get_absolute_url())
        response = self.client.get(tag.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        response = self.client.get(category.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/search', {'q': 'django'})
        self.assertEqual(response.status_code, 200)
        s = load_articletags(article)
        self.assertIsNotNone(s)

        self.client.login(username='liangliangyy', password='liangliangyy')

        response = self.client.get(reverse('blog:archives'))
        self.assertEqual(response.status_code, 200)

        p = Paginator(Article.objects.all(), settings.PAGINATE_BY)
        self.check_pagination(p, '', '')

        p = Paginator(Article.objects.filter(tags=tag), settings.PAGINATE_BY)
        self.check_pagination(p, '分类标签归档', tag.slug)

        p = Paginator(
            Article.objects.filter(
                author__username='liangliangyy'), settings.PAGINATE_BY)
        self.check_pagination(p, '作者文章归档', 'liangliangyy')

        p = Paginator(Article.objects.filter(category=category), settings.PAGINATE_BY)
        self.check_pagination(p, '分类目录归档', category.slug)

        f = BlogSearchForm()
        f.search()
        # self.client.login(username='liangliangyy', password='liangliangyy')
        from djangoblog.spider_notify import SpiderNotify
        SpiderNotify.baidu_notify([article.get_full_url()])

        from blog.templatetags.blog_tags import gravatar_url, gravatar
        u = gravatar_url('liangliangyy@gmail.com')
        u = gravatar('liangliangyy@gmail.com')

        link = Links(
            sequence=1,
            name="lylinux",
            link='https://wwww.lylinux.net')
        link.save()
        response = self.client.get('/links.html')
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/feed/')
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)

        self.client.get("/admin/blog/article/1/delete/")
        self.client.get('/admin/servermanager/emailsendlog/')
        self.client.get('/admin/admin/logentry/')
        self.client.get('/admin/admin/logentry/1/change/')

    # GJ: 辅助测试方法：遍历所有分页，验证上一页/下一页链接及返回状态码。
    def check_pagination(self, p, type, value):
        # GJ: 遍历每一页，加载分页信息并断言数据不为空。
        for page in range(1, p.num_pages + 1):
            s = load_pagination_info(p.page(page), type, value)
            self.assertIsNotNone(s)
            # GJ: 如果存在上一页链接，模拟点击并断言响应成功。
            if s['previous_url']:
                response = self.client.get(s['previous_url'])
                self.assertEqual(response.status_code, 200)
            if s['next_url']:
                response = self.client.get(s['next_url'])
                self.assertEqual(response.status_code, 200)

    # GJ: 测试用例：模拟从网络下载图片并保存到本地，验证静态资源处理逻辑。
    def test_image(self):
        import requests
        rsp = requests.get(
            'https://www.python.org/static/img/python-logo.png')
        imagepath = os.path.join(settings.BASE_DIR, 'python.png')
        with open(imagepath, 'wb') as file:
            file.write(rsp.content)
        rsp = self.client.post('/upload')
        self.assertEqual(rsp.status_code, 403)
        sign = get_sha256(get_sha256(settings.SECRET_KEY))
        with open(imagepath, 'rb') as file:
            imgfile = SimpleUploadedFile(
                'python.png', file.read(), content_type='image/jpg')
            form_data = {'python.png': imgfile}
            rsp = self.client.post(
                '/upload?sign=' + sign, form_data, follow=True)
            self.assertEqual(rsp.status_code, 200)
        os.remove(imagepath)
        from djangoblog.utils import save_user_avatar, send_email
        send_email(['qq@qq.com'], 'testTitle', 'testContent')
        save_user_avatar(
            'https://www.python.org/static/img/python-logo.png')

    # GJ: 测试异常页面：模拟访问不存在的路径，并断言返回 404 状态码。
    def test_errorpage(self):
        rsp = self.client.get('/eee')
        self.assertEqual(rsp.status_code, 404)

    # GJ: 测试后台命令与第三方配置：模拟创建超级管理员，并测试 OAuth 配置对象的创建。
    def test_commands(self):
        user = BlogUser.objects.get_or_create(
            email="liangliangyy@gmail.com",
            username="liangliangyy")[0]
        user.set_password("liangliangyy")
        user.is_staff = True
        user.is_superuser = True
        user.save()
        # GJ: 实例化第三方登录配置对象并赋值测试参数。
        c = OAuthConfig()
        c.type = 'qq'
        c.appkey = 'appkey'
        c.appsecret = 'appsecret'
        c.save()

        u = OAuthUser()
        u.type = 'qq'
        u.openid = 'openid'
        u.user = user
        u.picture = static("/blog/img/avatar.png")
        u.metadata = '''
{
"figureurl": "https://qzapp.qlogo.cn/qzapp/101513904/C740E30B4113EAA80E0D9918ABC78E82/30"
}'''
        u.save()

        u = OAuthUser()
        u.type = 'qq'
        u.openid = 'openid1'
        u.picture = 'https://qzapp.qlogo.cn/qzapp/101513904/C740E30B4113EAA80E0D9918ABC78E82/30'
        u.metadata = '''
        {
       "figureurl": "https://qzapp.qlogo.cn/qzapp/101513904/C740E30B4113EAA80E0D9918ABC78E82/30"
        }'''
        u.save()

        from blog.documents import ELASTICSEARCH_ENABLED
        if ELASTICSEARCH_ENABLED:
            call_command("build_index")
        call_command("ping_baidu", "all")
        call_command("create_testdata")
        call_command("clear_cache")
        call_command("sync_user_avatar")
        call_command("build_search_words")

# GJ: 搜索高亮功能测试类，用于验证关键词在文本中被正确匹配和标记。
class SearchHighlightTest(TestCase):
    """测试搜索高亮功能"""

    # GJ: 核心测试方法：验证搜索过滤器对不同大小写及多关键词的高亮处理逻辑。
    def test_highlight_search_term_filter(self):
        """测试标题高亮filter"""
        # 测试基本高亮
        text = "Django is a web framework"
        result = highlight_search_term(text, "django")
        self.assertIn("<mark>Django</mark>", result)
        self.assertIn("web framework", result)

        # 测试不区分大小写
        text = "Python and python"
        result = highlight_search_term(text, "PYTHON")
        self.assertEqual(result.count("<mark>"), 2)

        # 测试多个关键词
        text = "Django web framework with Python"
        result = highlight_search_term(text, "django python")
        self.assertIn("<mark>Django</mark>", result)
        self.assertIn("<mark>Python</mark>", result)

        # 测试空查询
        text = "Some text"
        result = highlight_search_term(text, "")
        self.assertEqual(result, text)

        # 测试空文本
        result = highlight_search_term("", "query")
        self.assertEqual(result, "")

    # GJ: 测试用例：验证正文过滤器的 HTML 内容高亮处理及标签清理逻辑。
    def test_highlight_content_filter(self):
        """测试正文高亮filter"""
        # 测试HTML内容高亮
        html = "<p>Django is a great web framework. Django makes development easy.</p>"
        result = highlight_content(html, "django")

        # 应该包含高亮标记
        self.assertIn("<mark>", result)
        self.assertIn("</mark>", result)

        # HTML标签应该被去除
        self.assertNotIn("<p>", result)

        # 应该包含Django关键词（不区分大小写）
        self.assertIn("django", result.lower())

        # 测试空查询
        result = highlight_content(html, "")
        self.assertEqual(result, html)

    # GJ: 测试用例：验证搜索页面的可访问性，并检查视图是否正确接收了查询参数。
    def test_search_page_access(self):
        """测试搜索页面访问"""
        # 测试搜索页面可以正常访问
        response = self.client.get('/search', {'q': 'django'})
        self.assertEqual(response.status_code, 200)

        # 检查响应中是否有查询参数
        self.assertIn('query', response.context)
        self.assertEqual(response.context['query'], 'django')

    # GJ: 测试用例：专门验证中文与英文混合场景下的关键词高亮匹配逻辑。
    def test_chinese_keyword_highlight(self):
        """测试中文关键词高亮"""
        text = "这是一个Django博客系统"
        result = highlight_search_term(text, "Django")
        self.assertIn("<mark>Django</mark>", result)

        # 测试中文关键词
        text = "欢迎使用DjangoBlog系统"
        result = highlight_search_term(text, "Django")
        self.assertIn("<mark>Django</mark>", result)
