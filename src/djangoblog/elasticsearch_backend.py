# zhang: 模块职责：实现 Elasticsearch 搜索后端、查询与搜索表单。
from django.utils.encoding import force_str
from elasticsearch_dsl import Q
from haystack.backends import BaseEngine, BaseSearchBackend, BaseSearchQuery, log_query
from haystack.forms import ModelSearchForm
from haystack.models import SearchResult
from haystack.utils import log as logging

from blog.documents import ArticleDocument, ArticleDocumentManager
from blog.models import Article

logger = logging.getLogger(__name__)


# zhang: 类职责：负责 Elasticsearch 索引与搜索适配。
class ElasticSearchBackend(BaseSearchBackend):
    # zhang: 方法职责：提供内部辅助处理逻辑：init。
    def __init__(self, connection_alias, **connection_options):
        super(
            ElasticSearchBackend,
            self).__init__(
            connection_alias,
            **connection_options)
        self.manager = ArticleDocumentManager()
        self.include_spelling = True

    # zhang: 方法职责：提供内部辅助处理逻辑：get models。
    def _get_models(self, iterable):
        models = iterable if iterable and iterable[0] else Article.objects.all()
        docs = self.manager.convert_to_doc(models)
        return docs

    # zhang: 方法职责：提供内部辅助处理逻辑：create。
    def _create(self, models):
        self.manager.create_index()
        docs = self._get_models(models)
        self.manager.rebuild(docs)

    # zhang: 方法职责：提供内部辅助处理逻辑：delete。
    def _delete(self, models):
        for m in models:
            m.delete()
        return True

    # zhang: 方法职责：提供内部辅助处理逻辑：rebuild。
    def _rebuild(self, models):
        models = models if models else Article.objects.all()
        docs = self.manager.convert_to_doc(models)
        self.manager.update_docs(docs)

    # zhang: 方法职责：同步索引数据。
    def update(self, index, iterable, commit=True):

        models = self._get_models(iterable)
        self.manager.update_docs(models)

    # zhang: 方法职责：从索引中删除记录。
    def remove(self, obj_or_string):
        models = self._get_models([obj_or_string])
        self._delete(models)

    # zhang: 方法职责：清空相关索引。
    def clear(self, models=None, commit=True):
        self.remove(None)

    # zhang: 方法职责：读取或生成 suggestion 相关数据。
    @staticmethod
    def get_suggestion(query: str) -> str:
        """获取推荐词, 如果没有找到添加原搜索词"""

        search = ArticleDocument.search() \
            .query("match", body=query) \
            .suggest('suggest_search', query, term={'field': 'body'}) \
            .execute()

        keywords = []
        for suggest in search.suggest.suggest_search:
            if suggest["options"]:
                keywords.append(suggest["options"][0]["text"])
            else:
                keywords.append(suggest["text"])

        return ' '.join(keywords)

    # zhang: 方法职责：执行查询并返回结果。
    @log_query
    def search(self, query_string, **kwargs):
        logger.info('search query_string:' + query_string)

        start_offset = kwargs.get('start_offset')
        end_offset = kwargs.get('end_offset')
        highlight = kwargs.get('highlight', True)  # 默认启用高亮

        # 推荐词搜索
        if getattr(self, "is_suggest", None):
            suggestion = self.get_suggestion(query_string)
        else:
            suggestion = query_string

        q = Q('bool',
              should=[Q('match', body=suggestion), Q('match', title=suggestion)],
              minimum_should_match=1)  # 至少匹配1个should子句

        search = ArticleDocument.search() \
                     .query('bool', filter=[q]) \
                     .filter('term', status='p') \
                     .filter('term', type='a')

        # 添加高亮配置
        if highlight:
            search = search.highlight('title', 'body',
                                    fragment_size=150,  # 片段大小
                                    number_of_fragments=3,  # 片段数量
                                    pre_tags=['<mark>'],  # 高亮开始标签
                                    post_tags=['</mark>'])  # 高亮结束标签

        search = search.source(False)[start_offset: end_offset]

        results = search.execute()
        # ES 8.x: total 现在是对象 {'value': 123, 'relation': 'eq'}
        hits_total = results['hits']['total']
        hits = hits_total['value'] if isinstance(hits_total, dict) else hits_total
        raw_results = []
        for raw_result in results['hits']['hits']:
            app_label = 'blog'
            model_name = 'Article'
            additional_fields = {}

            # 添加高亮内容
            if highlight and 'highlight' in raw_result:
                highlighted = {}
                if 'title' in raw_result['highlight']:
                    highlighted['title'] = raw_result['highlight']['title']
                if 'body' in raw_result['highlight']:
                    highlighted['body'] = raw_result['highlight']['body']

                if highlighted:
                    additional_fields['highlighted'] = highlighted

            result_class = SearchResult

            result = result_class(
                app_label,
                model_name,
                raw_result['_id'],
                raw_result['_score'],
                **additional_fields)
            raw_results.append(result)
        facets = {}
        spelling_suggestion = None if query_string == suggestion else suggestion

        return {
            'results': raw_results,
            'hits': hits,
            'facets': facets,
            'spelling_suggestion': spelling_suggestion,
        }


# zhang: 类职责：构造 Elasticsearch 查询参数。
class ElasticSearchQuery(BaseSearchQuery):
    # zhang: 方法职责：提供内部辅助处理逻辑：convert datetime。
    def _convert_datetime(self, date):
        if hasattr(date, 'hour'):
            return force_str(date.strftime('%Y%m%d%H%M%S'))
        else:
            return force_str(date.strftime('%Y%m%d000000'))

    # zhang: 方法职责：封装 clean 对应的处理步骤。
    def clean(self, query_fragment):
        """
        Provides a mechanism for sanitizing user input before presenting the
        value to the backend.

        Whoosh 1.X differs here in that you can no longer use a backslash
        to escape reserved characters. Instead, the whole word should be
        quoted.
        """
        words = query_fragment.split()
        cleaned_words = []

        for word in words:
            if word in self.backend.RESERVED_WORDS:
                word = word.replace(word, word.lower())

            for char in self.backend.RESERVED_CHARACTERS:
                if char in word:
                    word = "'%s'" % word
                    break

            cleaned_words.append(word)

        return ' '.join(cleaned_words)

    # zhang: 方法职责：构造 query fragment 相关结构。
    def build_query_fragment(self, field, filter_type, value):
        return value.query_string

    # zhang: 方法职责：读取或生成 count 相关数据。
    def get_count(self):
        results = self.get_results()
        return len(results) if results else 0

    # zhang: 方法职责：读取或生成 spelling suggestion 相关数据。
    def get_spelling_suggestion(self, preferred_query=None):
        return self._spelling_suggestion

    # zhang: 方法职责：整理搜索参数。
    def build_params(self, spelling_query=None):
        kwargs = super(ElasticSearchQuery, self).build_params(spelling_query=spelling_query)
        return kwargs


# zhang: 类职责：处理搜索表单及结果。
class ElasticSearchModelSearchForm(ModelSearchForm):

    # zhang: 方法职责：执行查询并返回结果。
    def search(self):
        # 是否建议搜索
        self.searchqueryset.query.backend.is_suggest = self.data.get("is_suggest") != "no"
        sqs = super().search()
        return sqs


# zhang: 类职责：向 Haystack 注册 Elasticsearch 后端。
class ElasticSearchEngine(BaseEngine):
    backend = ElasticSearchBackend
    query = ElasticSearchQuery
