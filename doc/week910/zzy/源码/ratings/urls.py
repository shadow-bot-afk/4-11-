from django.urls import path
from . import views

app_name = 'ratings'
urlpatterns = [
    # zzy: 提交/修改评分(POST)，查询统计(GET)
    path('rate/<int:article_id>/', views.rate, name='rate'),
    path('stats/<int:article_id>/', views.stats, name='stats'),
]