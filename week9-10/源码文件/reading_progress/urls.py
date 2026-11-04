from django.urls import path
from . import views

urlpatterns = [
    path("", views.ReadProgressView.as_view(), name="reading-progress"),
]