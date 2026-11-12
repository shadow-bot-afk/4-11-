from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from blog.models import Article


class Rating(models.Model):
    # zzy: 电影评分记录：一条记录 = 一个用户对一篇文章的当前评分
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='ratings', verbose_name='评分用户')
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE,
        related_name='ratings', verbose_name='电影文章')
    # zzy: 评分只允许1-5星整数，数据库层用校验器限制非法分值
    score = models.PositiveSmallIntegerField(
        '评分(1-5星)',
        validators=[MinValueValidator(1), MaxValueValidator(5)])
    created_time = models.DateTimeField('创建时间', auto_now_add=True)
    last_modify_time = models.DateTimeField('修改时间', auto_now=True)

    class Meta:
        verbose_name = '电影评分'
        verbose_name_plural = verbose_name
        # zzy: 同一用户对同一文章只允许一条评分，唯一约束从数据库层防止重复记录
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'article'], name='unique_user_article_rating')
        ]

    def __str__(self):
        return f'{self.user} 给《{self.article}》评 {self.score} 星'