from django.http import JsonResponse
from django.views import View
from .models import ArticleReadProgress

class ReadProgressView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"progress": 0})
        aid = request.GET.get("article_id")
        if not aid:
            return JsonResponse({"progress": 0})
        obj, _ = ArticleReadProgress.objects.get_or_create(user=request.user, article_id=int(aid))
        return JsonResponse({"progress": obj.progress})

    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"code": 401, "msg": "未登录"})
        aid = request.POST.get("article_id")
        p = float(request.POST.get("progress", 0))
        if not aid:
            return JsonResponse({"code": 400})
        obj, _ = ArticleReadProgress.objects.get_or_create(user=request.user, article_id=int(aid))
        # 超过98%标记为读完
        if p >= 0.98:
            obj.is_finish = True
        obj.progress = p
        obj.save()
        return JsonResponse({"code": 200})