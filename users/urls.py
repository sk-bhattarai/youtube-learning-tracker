from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('settings/', views.account_settings, name='account_settings'),
    path('profile/', views.profile, name='profile'),
    path('api/users/streak/', views.get_user_streak, name='get_user_streak'),
] 