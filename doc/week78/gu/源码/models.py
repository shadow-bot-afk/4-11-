# gys: 本模块定义了评论相关的数据模型，包含评论内容(Comment)和评论Emoji反应(CommentReaction)。
# gys: 主要涉及评论与文章、用户的外键关联，以及评论的层级回复（通过 parent_comment 自关联）。
from django.conf import settings
from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from blog.models import Article


# Create your models here.

class Comment(models.Model):
    # gys: 评论正文，最大长度 300 字符
    body = models.TextField('正文', max_length=300)
    # gys: 评论创建时间，默认为当前时间
    creation_time = models.DateTimeField(_('creation time'), default=now)
    # gys: 评论最后修改时间，默认为当前时间
    last_modify_time = models.DateTimeField(_('last modify time'), default=now)
    # gys: 评论作者，关联到系统的用户模型（AUTH_USER_MODEL），级联删除
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('author'),
        on_delete=models.CASCADE)
    # gys: 评论所属文章，关联到 blog 应用的 Article 模型，级联删除
    article = models.ForeignKey(
        Article,
        verbose_name=_('article'),
        on_delete=models.CASCADE)
    # gys: 父评论，用于实现回复功能。自关联，可以为空（表示这是一级评论）
    parent_comment = models.ForeignKey(
        'self',
        verbose_name=_('parent comment'),
        blank=True,
        null=True,
        on_delete=models.CASCADE)
    # gys: 评论是否启用（审核通过）。默认 False，表示需要管理员审核
    is_enable = models.BooleanField(_('enable'),
                                    default=False, blank=False, null=False)

    class Meta:
        # gys: 默认按 ID 倒序排列，即最新的评论显示在最前面
        ordering = ['-id']
        verbose_name = _('comment')
        verbose_name_plural = verbose_name
        get_latest_by = 'id'
        indexes = [
            # gys: 优化评论列表查询：article + parent_comment + is_enable组合索引
            models.Index(fields=['article', 'parent_comment', 'is_enable'], name='idx_art_parent_enable'),
            # gys: 优化侧边栏评论查询：is_enable + id组合索引
            models.Index(fields=['is_enable', '-id'], name='idx_enable_id'),
        ]

    def __str__(self):
        # gys: 定义对象的字符串表示，返回评论正文，方便在后台管理界面显示
        return self.body

    # gys: 获取当前评论的 Emoji 反应统计信息
    # gys: 返回一个字典，包含每种 Emoji 的数量、当前用户是否已反应、以及反应过的用户名列表
    def get_reactions_summary(self, user=None):
        """
        获取评论的 reactions 统计信息
        返回格式: {
            '👍': {
                'count': 5,
                'has_reacted': True,
                'users': ['Alice', 'Bob', 'Charlie']
            },
            '❤️': {'count': 3, 'has_reacted': False, 'users': [...]},
            ... 
        }
        """
        from django.db.models import Count

        # gys: 按 reaction_type 分组统计当前评论的每种 Emoji 的数量
        reactions = CommentReaction.objects.filter(
            comment=self
        ).values('reaction_type').annotate(count=Count('id'))

        result = {}
        # gys: 遍历统计结果，组装每种 Emoji 的详细信息
        for reaction in reactions:
            emoji = reaction['reaction_type']

            # gys: 获取该 emoji 的所有点赞用户（使用 select_related 优化查询，最多显示10个用户）
            reaction_users = CommentReaction.objects.filter(
                comment=self,
                reaction_type=emoji
            ).select_related('user')[:10]

            # gys: 提取用户昵称（如果没有昵称则用用户名）
            user_names = [r.user.nickname or r.user.username for r in reaction_users]

            result[emoji] = {
                'count': reaction['count'],
                'has_reacted': False,
                'users': user_names
            }

            # gys: 如果当前请求包含已登录用户，则检查该用户是否点过这个 Emoji
            if user and user.is_authenticated:
                result[emoji]['has_reacted'] = CommentReaction.objects.filter(
                    comment=self,
                    user=user,
                    reaction_type=emoji
                ).exists()

        return result


# gys: 评论的 Emoji 反应/点赞数据模型
class CommentReaction(models.Model):
    """
    评论的 Emoji 反应/点赞
    """
    # gys: 预定义的 Emoji 类型选项
    REACTION_CHOICES = [
        ('👍', 'thumbs_up'),
        ('👎', 'thumbs_down'),
        ('❤️', 'heart'),
        ('😄', 'laugh'),
        ('🎉', 'hooray'),
        ('😕', 'confused'),
        ('🚀', 'rocket'),
        ('👀', 'eyes'),
    ]

    # gys: 关联的评论对象，级联删除，反向查询名为 reactions
    comment = models.ForeignKey(
        Comment,
        verbose_name=_('comment'),
        on_delete=models.CASCADE,
        related_name='reactions'
    )
    # gys: 点反应的操作用户
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('user'),
        on_delete=models.CASCADE
    )
    # gys: 反应的类型（Emoji），受 REACTION_CHOICES 约束
    reaction_type = models.CharField(
        _('reaction type'),
        max_length=10,
        choices=REACTION_CHOICES
    )
    # gys: 点反应的时间，自动记录为当前时间
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('comment reaction')
        verbose_name_plural = _('comment reactions')
        # gys: 每个用户对同一评论的同一种 emoji 只能点一次
        unique_together = ['comment', 'user', 'reaction_type']
        indexes = [
            # gys: 优化针对某一评论的特定 Emoji 查询
            models.Index(fields=['comment', 'reaction_type'], name='idx_comment_reaction'),
        ]

    def __str__(self):
        # gys: 返回包含用户名、Emoji 和评论ID的字符串表示
        return f'{self.user.username} - {self.reaction_type} on comment {self.comment.id}'
        