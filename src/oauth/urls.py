from django.urls import path

from . import views

app_name = "oauth"
# sw: oauth应用路由配置，定义第三方登录相关接口地址
urlpatterns = [
# sw: 授权回调地址，第三方平台回调回来的接口
    path(
        r'oauth/authorize',
        views.authorize),
# sw: 缺少邮箱时，填写邮箱表单页面
    path(
        r'oauth/requireemail/<int:oauthid>.html',
        views.RequireEmailView.as_view(),
        name='require_email'),
# sw: 邮箱确认链接路由，校验签名完成绑定
    path(
        r'oauth/emailconfirm/<int:id>/<sign>.html',
        views.emailconfirm,
        name='email_confirm'),
# sw: 绑定成功结果展示页
    path(
        r'oauth/bindsuccess/<int:oauthid>.html',
        views.bindsuccess,
        name='bindsuccess'),
# sw: 第三方登录入口，跳转到对应平台授权页
    path(
        r'oauth/oauthlogin',
        views.oauthlogin,
        name='oauthlogin')]
