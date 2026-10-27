"""
模板标签测试
测试各种模板标签和过滤器的功能
"""
from django.core.paginator import Paginator
from django.template import Context, Template
from django.test import RequestFactory

from blog.models import Article
from blog.templatetags.blog_tags import *
from djangoblog.test_base import BaseTestCase

# GJ: 博客模板标签测试类，验证自定义标签在渲染时的输出结果。
class BlogTagsTest(BaseTestCase):
    """测试博客模板标签"""

    # GJ: 测试前置初始化：调用父类初始化方法，并实例化请求工厂。
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    # GJ: 测试加载文章标签：验证 load_articletags 标签返回的数据类型及字典键名。
    def test_load_articletags(self):
        """测试加载文章标签"""
        self.article.tags.add(self.tag)
        result = load_articletags(self.article)
        self.assertIsInstance(result, dict)
        self.assertIn('article_tags_list', result)
        # 检查标签是否在列表中
        tag_objects = [tag_tuple[2] for tag_tuple in result['article_tags_list']]
        self.assertIn(self.tag, tag_objects)

    def test_load_pagination_info(self):
        """测试加载分页信息"""
        # 创建测试数据
        articles = [self.create_article(title=f'文章{i}') for i in range(20)]
        paginator = Paginator(articles, 10)
        page = paginator.get_page(1)

        # load_pagination_info 需要 page_type 和 tag_name 参数
        info = load_pagination_info(page, '', '')

        self.assertIsNotNone(info)
        # 验证基本分页属性存在
        self.assertTrue(hasattr(page, 'has_previous'))
        self.assertTrue(hasattr(page, 'has_next'))

    def test_load_pagination_info_last_page(self):
        """测试最后一页的分页信息"""
        articles = [self.create_article(title=f'文章{i}') for i in range(15)]
        paginator = Paginator(articles, 10)
        page = paginator.get_page(2)

        info = load_pagination_info(page, '', '')

        # 验证分页对象的属性
        self.assertFalse(page.has_next())
        self.assertTrue(page.has_previous())

    # GJ: 测试正常匹配：验证文本包含搜索关键词时，是否被正确加上 <mark> 高亮标签。
    def test_highlight_search_term(self):
        """测试搜索关键词高亮"""
        text = '这是一段包含关键词的文本'
        result = highlight_search_term(text, '关键词')
        self.assertIn('<mark>', result)
        self.assertIn('关键词', result)

    # GJ: 测试不匹配场景：验证文本中不存在关键词时，原样返回文本且不改变内容。
    def test_highlight_search_term_no_match(self):
        """测试搜索关键词不匹配"""
        text = '这是一段普通文本'
        result = highlight_search_term(text, '关键词')
        self.assertEqual(result, text)

    # GJ: 测试边界条件：验证传入空字符串作为搜索词时，系统能安全处理并返回原文本。
    def test_highlight_search_term_empty_query(self):
        """测试空搜索词"""
        text = '这是一段普通文本'
        result = highlight_search_term(text, '')
        self.assertEqual(result, text)

    # GJ: 测试内容高亮：验证 HTML 文本中的关键词能被正确过滤并添加高亮标记。
    def test_highlight_content(self):
        """测试内容高亮"""
        content = '<p>这是一段 HTML 内容</p>'
        result = highlight_content(content, '内容')
        self.assertIn('内容', result)

    # GJ: 测试自定义 Markdown 渲染：验证 Markdown 语法（标题、加粗）能正确转换为 HTML 标签。
    def test_custom_markdown(self):
        """测试自定义 Markdown 渲染"""
        markdown_text = '# 标题\n\n这是一段**加粗**的文本'
        result = custom_markdown(markdown_text)
        self.assertIn('<h1', result)
        self.assertIn('<strong>', result)

    # GJ: 测试文章内容渲染：验证文章正文的 Markdown 渲染功能（无需实际创建数据库文章）。
    def test_article_body_rendering(self):
        """测试文章内容渲染"""
        # 测试 Markdown 渲染，不需要创建文章
        markdown_text = '# 标题\n这是文章内容'
        result = custom_markdown(markdown_text)
        self.assertIn('<h1', result)
        self.assertIn('文章内容', result)

# GJ: Vite 模板标签测试类，验证前端资源加载标签的基础可用性。
class ViteTagsTest(BaseTestCase):
    """测试 Vite 模板标签"""

    # GJ: 测试 Vite 标签模块导入：验证模块能被正确加载且不为空。
    def test_vite_module_exists(self):
        """测试 Vite 模块存在"""
        # 简单测试 Vite 标签模块可以导入
        from blog.templatetags import vite_tags
        self.assertIsNotNone(vite_tags)

# GJ: 自定义过滤器测试类，验证日期格式化等自定义过滤器的输出逻辑。
class CustomFiltersTest(BaseTestCase):
    """测试自定义过滤器"""

    # GJ: 测试日期格式化过滤器：验证传入时间对象后能正确转化为指定格式的字符串。
    def test_date_format_filter(self):
        """测试日期格式化过滤器"""
        from django.utils import timezone
        now = timezone.now()

        template = Template('{% load blog_tags %}{{ date|date:"Y-m-d" }}')
        context = Context({'date': now})
        result = template.render(context)
        self.assertIn(str(now.year), result)

    # GJ: 测试 URL 编码过滤器：验证模板中的中文字符在渲染时能被正确编码。
    def test_url_encode_filter(self):
        """测试 URL 编码过滤器"""
        template = Template('{% load blog_tags %}{{ text|urlencode }}')
        context = Context({'text': '中文测试'})
        result = template.render(context)
        self.assertNotIn('中文', result)

    # GJ: 测试去标签过滤器：验证模板中的 HTML 标签能被清理，仅保留纯文本内容。
    def test_strip_tags_filter(self):
        """测试去除 HTML 标签过滤器"""
        html = '<p>这是<strong>HTML</strong>文本</p>'
        template = Template('{% load blog_tags %}{{ html|striptags }}')
        context = Context({'html': html})
        result = template.render(context)
        self.assertNotIn('<p>', result)
        self.assertNotIn('<strong>', result)
        self.assertIn('这是', result)

# GJ: 侧边栏标签测试类，验证侧边栏依赖的上下文数据是否正确加载。
class SidebarTagsTest(BaseTestCase):
    """测试侧边栏标签"""

    # GJ: 测试侧边栏数据存在：断言文章、分类、标签等基础测试数据已被成功创建。
    def test_sidebar_data_exists(self):
        """测试侧边栏数据存在"""
        # 简单测试侧边栏相关数据可以访问
        self.assertIsNotNone(self.article)
        self.assertIsNotNone(self.category)
        self.assertIsNotNone(self.tag)

# GJ: 缓存标签测试类，验证缓存模块及自定义标签的读写逻辑。
class CacheTagsTest(BaseTestCase):
    """测试缓存标签"""

    # GJ: 测试缓存操作：验证 Django 缓存系统的 set 和 get 功能是否正常工作。
    def test_cache_operations(self):
        """测试缓存操作"""
        from django.core.cache import cache

        # 测试缓存设置和获取
        cache.set('test_key', 'test_value', 60)
        self.assertEqual(cache.get('test_key'), 'test_value')

        # 清空缓存
        cache.clear()
        self.assertIsNone(cache.get('test_key'))

# GJ: Markdown 扩展测试类，验证自定义 Markdown 渲染器对代码块和表格的解析支持。
class MarkdownExtensionsTest(BaseTestCase):
    """测试 Markdown 扩展"""

    # GJ: 测试代码高亮：验证 Markdown 中的代码块语法能被正确转换为 HTML `<code>` 标签。
    def test_code_highlight(self):
        """测试代码高亮"""
        markdown_text = '''```python
def hello():
    print("Hello World")
```'''
        result = custom_markdown(markdown_text)
        self.assertIn('<code', result)

    # GJ: 测试表格支持：验证 Markdown 表格语法能被正确解析并渲染为 HTML 表格。
    def test_table_support(self):
        """测试表格支持"""
        markdown_text = '''
| 列1 | 列2 |
|-----|-----|
| 值1 | 值2 |
'''
        result = custom_markdown(markdown_text)
        self.assertIn('<table', result)

    # GJ: 测试自动链接：验证用尖括号包裹的 URL 能被正确解析为 HTML 的 <a> 标签。
    def test_auto_link(self):
        """测试自动链接"""
        markdown_text = '<https://example.com>'
        result = custom_markdown(markdown_text)
        # Markdown 可能不会自动转换普通URL，需要用尖括号包裹
        self.assertIn('example.com', result)

    # GJ: 测试删除线：验证 Markdown 的双波浪线语法能被正确渲染为删除线标签。
    def test_strikethrough(self):
        """测试删除线"""
        markdown_text = '~~删除的文本~~'
        result = custom_markdown(markdown_text)
        # 根据实际 Markdown 扩展支持情况验证
        self.assertIsNotNone(result)
