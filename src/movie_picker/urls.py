
"""随机选片应用的URL路由。"""

from django.urls import path
from . import views

app_name = 'movie_picker'

urlpatterns = [
    path('', views.movie_picker_view, name='index'),
]
