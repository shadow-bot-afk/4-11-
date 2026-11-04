from django.db import models
from django.conf import settings

class ArticleReadProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="用户")
    article_id = models.IntegerField(verbose_name="文章ID")
    progress = models.FloatField(default=0.0, verbose_name="阅读进度 0~1")
    is_finish = models.BooleanField(default=False, verbose_name="是否读完")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        unique_together = ["user", "article_id"]
        verbose_name = "文章阅读进度"