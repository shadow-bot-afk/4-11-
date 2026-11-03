from django.urls import path
from . import views

urlpatterns = [
    path('toggle/<int:article_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('my/', views.my_favorites, name='my_favorites'),
]