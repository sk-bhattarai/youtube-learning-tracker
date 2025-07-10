from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .models import CustomUser

def home(request):
    """Home page view"""
    if request.user.is_authenticated:
        return redirect('users:dashboard')
    return render(request, 'users/home.html')

@login_required
def dashboard(request):
    """User dashboard view"""
    from playlists.models import Playlist, Video
    from progress.models import LearningStreak, DailyGoal
    
    # Get user's playlists
    playlists = Playlist.objects.filter(user=request.user)
    
    # Get learning streak
    streak, created = LearningStreak.objects.get_or_create(user=request.user)
    
    # Get today's goal and completed videos
    today = timezone.now().date()
    daily_goal, created = DailyGoal.objects.get_or_create(
        user=request.user,
        date=today,
        defaults={'videos_planned': 0}
    )
    
    # Count videos completed today across all playlists
    videos_completed_today = Video.objects.filter(
        playlist__user=request.user,
        is_completed=True,
        completed_at__date=today
    ).count()
    
    # Update daily goal with completed videos
    daily_goal.update_progress(videos_completed_today)
    
    context = {
        'playlists': playlists,
        'streak': streak,
        'daily_goal': daily_goal,
    }
    return render(request, 'users/dashboard.html', context)

@login_required
def account_settings(request):
    """User settings view"""
    if request.method == 'POST':
        # Update notification settings
        notification_time = request.POST.get('notification_time')
        notifications_enabled = request.POST.get('notifications_enabled') == 'on'
        
        request.user.preferred_learning_time = notification_time
        request.user.notification_enabled = notifications_enabled
        request.user.save()
        
        messages.success(request, 'Settings updated successfully!')
        return redirect('users:dashboard')
    
    return render(request, 'users/settings.html')

@login_required
def profile(request):
    """User profile view"""
    if request.method == 'POST':
        user = request.user
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        user.preferred_learning_time = request.POST.get('preferred_learning_time')
        user.notification_enabled = request.POST.get('notification_enabled') == 'on'
        
        if request.FILES.get('profile_photo'):
            user.profile_photo = request.FILES['profile_photo']
        
        user.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('users:profile')
        
    return render(request, 'users/profile.html')

@login_required
def get_user_streak(request):
    """API endpoint to get user's current streak"""
    from playlists.models import Video
    from progress.models import LearningStreak
    
    streak, created = LearningStreak.objects.get_or_create(user=request.user)
    
    # Get today's completion count
    today = timezone.now().date()
    videos_completed_today = Video.objects.filter(
        playlist__user=request.user,
        is_completed=True,
        completed_at__date=today
    ).count()
    
    return JsonResponse({
        'current_streak': streak.current_streak,
        'longest_streak': streak.longest_streak,
        'last_activity_date': streak.last_activity_date.strftime('%Y-%m-%d') if streak.last_activity_date else None,
        'videos_completed_today': videos_completed_today,
    })
