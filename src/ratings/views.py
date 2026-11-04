from django.db import models
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from blog.models import Article
from .models import Rating


@login_required
@require_POST
def rate(request, article_id):
    # zzy: 提交或修改评分；仅接受1-5星，同一用户同一文章只保留一条记录
    article = get_object_or_404(Article, pk=article_id)
    try:
        score = int(request.POST.get('score', '0'))
    except ValueError:
        score = 0
    # zzy: 非法分值(非1-5)直接拒绝，不写入数据库
    if score < 1 or score > 5:
        return JsonResponse({'success': False, 'msg': '评分必须为1-5星'}, status=400)

    # zzy: 有记录则修改(同一用户只维护一条)，无则创建；唯一约束兜底防并发重复
    rating, created = Rating.objects.update_or_create(
        user=request.user, article=article,
        defaults={'score': score})

    avg, count = _get_stats(article)
    return JsonResponse({
        'success': True, 'created': created,
        'score': score, 'avg': avg, 'count': count})


def stats(request, article_id):
    # zzy: 查询文章的平均分和评分人数，无评分时返回None，避免除零
    article = get_object_or_404(Article, pk=article_id)
    avg, count = _get_stats(article)
    my_score = None
    if request.user.is_authenticated:
        r = Rating.objects.filter(user=request.user, article=article).first()
        my_score = r.score if r else None
    return JsonResponse({'avg': avg, 'count': count, 'my_score': my_score})


def _get_stats(article):
    # zzy: 平均分四舍五入保留1位小数；count为0时返回None，调用方显示"暂无评分"
    agg = Rating.objects.filter(article=article).aggregate(
        avg=models.Avg('score'), count=models.Count('id'))
    count = agg['count'] or 0
    avg = round(agg['avg'], 1) if count else None
    return avg, count