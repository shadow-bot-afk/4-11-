
"""随机选片功能：根据文章分类随机推荐已发布的电影。"""

from django.shortcuts import render

from blog.models import Article, Category


def movie_picker_view(request):
    """展示分类选项，并按用户选择随机抽取电影。"""

    # 仅允许抽取已发布的普通文章
    published_articles = Article.objects.filter(
        status='p',
        type='a'
    )

    # 只显示存在已发布文章的分类
    categories = Category.objects.filter(
        id__in=published_articles.values('category_id')
    ).order_by('name')

    # 获取用户选择的分类，空字符串代表全部分类
    raw_category = request.GET.get('category', '')
    selected_category = (
        int(raw_category) if raw_category.isdecimal() else None
    )

    # 按选择的分类筛选
    candidates = published_articles
    if selected_category is not None:
        candidates = candidates.filter(category_id=selected_category)

    # 点击抽取按钮后才执行随机查询
    movie = None
    has_picked = request.GET.get('pick') == '1'

    if has_picked:
        movie = candidates.select_related('category').order_by('?').first()

    context = {
        'categories': categories,
        'selected_category': selected_category,
        'movie': movie,
        'has_picked': has_picked,
    }

    return render(request, 'movie_picker/index.html', context)
