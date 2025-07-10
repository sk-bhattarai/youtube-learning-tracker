from django.urls import path
from . import views

app_name = 'playlists'

urlpatterns = [
    path('', views.playlist_list, name='playlist_list'),
    path('add/', views.add_playlist, name='add_playlist'),
    path('<int:pk>/', views.playlist_detail, name='playlist_detail'),
    path('<int:pk>/edit/', views.playlist_edit, name='playlist_edit'),
    path('<int:pk>/delete/', views.playlist_delete, name='playlist_delete'),
    path('video/<int:video_id>/complete/', views.update_video_progress, name='update_video_progress'),
    path('test-api/', views.test_youtube_api, name='test_youtube_api'),
    
    # API endpoints
    path('api/playlists/fetch-info/', views.fetch_playlist_info, name='fetch_playlist_info'),
    path('api/users/streak/', views.get_user_streak, name='get_user_streak'),
] 