from django.db import models
from django.conf import settings
from blog.models import Article

class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="用户")
    article = models.ForeignKey(Article, on_delete=models.CASCADE, verbose_name="文章")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="收藏时间")

    class Meta:
        # 数据库层面约束：防止同一用户重复收藏同一文章
        unique_together = ('user', 'article')
        verbose_name = "电影收藏"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user.username} 收藏了 {self.article.title}"

# Create your models here.
