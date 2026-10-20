# gys: 本模块定义了评论相关的视图逻辑，包含评论提交视图(CommentPostView)和评论Emoji反应API(CommentReactionView)。
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from accounts.models import BlogUser
from blog.models import Article
from djangoblog.base_views import AuthenticatedFormView
from .forms import CommentForm
from .models import Comment, CommentReaction

# gys: 评论提交视图类，继承自 AuthenticatedFormView（自动处理登录验证和 CSRF 保护）
class CommentPostView(AuthenticatedFormView):
    """
    评论提交视图

    使用 AuthenticatedFormView 基类，自动提供：
    - 登录验证（未登录用户会被重定向）
    - CSRF 保护
    """
    form_class = CommentForm
    template_name = 'blog/article_detail.html'

    # gys: 处理 GET 请求，重定向到文章详情的评论区
    def get(self, request, *args, **kwargs):
        article_id = self.kwargs['article_id']
        article = get_object_or_404(Article, pk=article_id)
        url = article.get_absolute_url()
        return HttpResponseRedirect(url + "#comments")

    # gys: 处理表单验证失败的情况，重新渲染文章详情页并带回表单错误信息
    def form_invalid(self, form):
        article_id = self.kwargs['article_id']
        article = get_object_or_404(Article, pk=article_id)

        return self.render_to_response({
            'form': form,
            'article': article
        })

    # gys: 处理表单验证通过后的逻辑，保存评论数据
    def form_valid(self, form):
        """提交的数据验证合法后的逻辑"""
        user = self.request.user
        # gys: 原代码这里多写了一步 BlogUser.objects.get()，可以直接使用 user 或 user.bloguser
        author = BlogUser.objects.get(pk=user.pk) 
        article_id = self.kwargs['article_id']
        article = get_object_or_404(Article, pk=article_id)
        # gys: 检查文章或全局是否关闭了评论功能
        if article.comment_status == 'c' or article.status == 'c':
            raise ValidationError("该文章评论已关闭.")
        # gys: 先不直接保存，等补充完关联字段后再保存
        comment = form.save(False)
        comment.article = article
        # gys: 获取博客全局设置，判断评论是否需要审核
        from djangoblog.utils import get_blog_setting
        settings = get_blog_setting()
        if not settings.comment_need_review:
            comment.is_enable = True   
        comment.author = author

        # gys: 如果表单中携带了父评论 ID，说明这是回复，需要绑定父评论
        if form.cleaned_data['parent_comment_id']:
            parent_comment = Comment.objects.get(
                pk=form.cleaned_data['parent_comment_id'])
            comment.parent_comment = parent_comment

        # gys: 保存评论，并重定向到该评论的锚点位置
        comment.save(True)
        return HttpResponseRedirect(
            "%s#div-comment-%d" %
            (article.get_absolute_url(), comment.pk))


# gys: 评论 Emoji 反应 API 视图，处理获取和切换点赞状态
class CommentReactionView(View):
    """
    评论 Emoji 反应 API
    GET /comment/<comment_id>/react - 获取 reactions（公开）
    POST /comment/<comment_id>/react - 切换 reaction（需要登录）
    """

    # gys: 处理 GET 请求，返回指定评论的 Emoji 统计信息
    def get(self, request, comment_id):
        """获取评论的 reactions 数据（公开访问）"""
        comment = get_object_or_404(Comment, id=comment_id, is_enable=True)

        # gys: 传递用户信息，如果未登录则传递 None
        user = request.user if request.user.is_authenticated else None
        reactions_data = comment.get_reactions_summary(user)

        return JsonResponse({
            'success': True,
            'reactions': reactions_data
        })

    # gys: 处理 POST 请求，进行点赞/取消点赞操作（需登录）
    def post(self, request, comment_id):
        # gys: POST 需要登录验证，未登录直接返回 401
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        # gys: 获取评论（只有已启用的评论才能点赞）
        comment = get_object_or_404(Comment, id=comment_id, is_enable=True)

        # gys: 获取并校验 reaction 类型
        reaction_type = request.POST.get('reaction_type')

        # gys: 验证 reaction_type 是否合法，防止非法输入
        valid_reactions = [choice[0] for choice in CommentReaction.REACTION_CHOICES]
        if reaction_type not in valid_reactions:
            return JsonResponse({
                'error': 'Invalid reaction type'
            }, status=400)

        # gys: 切换 reaction（如果已存在则删除，否则创建）
        reaction, created = CommentReaction.objects.get_or_create(
            comment=comment,
            user=request.user,
            reaction_type=reaction_type
        )

        if not created:
            # gys: 已存在，删除它（取消点赞）
            reaction.delete()
            action = 'removed'
        else:
            action = 'added'

        # gys: 返回该评论最新的所有 reactions 统计数据
        reactions_data = comment.get_reactions_summary(request.user)

        return JsonResponse({
            'success': True,
            'action': action,
            'reactions': reactions_data
        })
        