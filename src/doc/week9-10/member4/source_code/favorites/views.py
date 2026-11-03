from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Favorite
from blog.models import Article

@login_required
def toggle_favorite(request, article_id):
    """处理收藏/取消收藏（AJAX请求）"""
    if request.method == 'POST':
        article = get_object_or_404(Article, id=article_id)
        favorite, created = Favorite.objects.get_or_create(user=request.user, article=article)
        
        if not created:
            # 如果已经存在，说明是取消收藏
            favorite.delete()
            return JsonResponse({'status': 'success', 'action': 'unfavorited'})
        
        return JsonResponse({'status': 'success', 'action': 'favorited'})
    return JsonResponse({'status': 'error', 'msg': 'Invalid request'}, status=400)

@login_required
def my_favorites(request):
    """展示我的收藏列表"""
    favorites = Favorite.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'favorites/my_favorites.html', {'favorites': favorites})

# Create your views here.
