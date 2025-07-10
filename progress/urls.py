from django.urls import path
from . import views

app_name = 'progress'

urlpatterns = [
    path('', views.progress_overview, name='progress_overview'),
    path('stats/', views.progress_stats, name='progress_stats'),
    path('api/streak/', views.update_streak, name='update_streak'),
    path('api/daily-goal/', views.update_daily_goal, name='update_daily_goal'),
] 