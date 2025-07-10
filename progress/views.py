from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from .models import LearningSession, LearningStreak, DailyGoal
from datetime import timedelta

# Create your views here.

@login_required
def progress_overview(request):
    """Display user's learning progress overview"""
    # Get user's learning sessions
    sessions = LearningSession.objects.filter(user=request.user)
    
    # Get streak information
    streak, created = LearningStreak.objects.get_or_create(user=request.user)
    
    # Get daily goals
    today = timezone.now().date()
    daily_goals = DailyGoal.objects.filter(
        user=request.user,
        date__gte=today - timedelta(days=7)
    ).order_by('-date')
    
    # Calculate completion rate for each day
    daily_stats = []
    for goal in daily_goals:
        completion_rate = (goal.videos_completed / goal.videos_planned * 100) if goal.videos_planned > 0 else 0
        daily_stats.append({
            'date': goal.date,
            'completion_rate': round(completion_rate, 1),
            'videos_completed': goal.videos_completed,
            'videos_planned': goal.videos_planned,
        })
    
    context = {
        'sessions': sessions,
        'streak': streak,
        'daily_stats': daily_stats,
    }
    return render(request, 'progress/overview.html', context)

@login_required
def progress_stats(request):
    """Display detailed learning statistics"""
    from playlists.models import Video  # Import moved here
    
    # Get total learning time
    total_duration = timedelta()
    completed_videos = Video.objects.filter(
        playlist__user=request.user,
        is_completed=True
    )
    
    for video in completed_videos:
        total_duration += video.duration
    
    # Get daily completion rates for the past 30 days
    today = timezone.now().date()
    start_date = today - timedelta(days=30)
    
    daily_goals = DailyGoal.objects.filter(
        user=request.user,
        date__gte=start_date
    ).order_by('date')
    
    completion_data = []
    for goal in daily_goals:
        completion_rate = (goal.videos_completed / goal.videos_planned * 100) if goal.videos_planned > 0 else 0
        completion_data.append({
            'date': goal.date.strftime('%Y-%m-%d'),
            'rate': round(completion_rate, 1)
        })
    
    # Get streak information
    streak = LearningStreak.objects.get(user=request.user)
    
    context = {
        'total_duration': total_duration,
        'videos_completed': completed_videos.count(),
        'completion_data': completion_data,
        'current_streak': streak.current_streak,
        'longest_streak': streak.longest_streak,
    }
    return render(request, 'progress/stats.html', context)

@login_required
def update_streak(request):
    """API endpoint for updating learning streak"""
    if request.method == 'POST':
        streak = LearningStreak.objects.get(user=request.user)
        streak.update_streak(timezone.now().date())
        
        return JsonResponse({
            'success': True,
            'current_streak': streak.current_streak,
            'longest_streak': streak.longest_streak,
        })
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def update_daily_goal(request):
    """API endpoint for updating daily goal"""
    if request.method == 'POST':
        videos_planned = int(request.POST.get('videos_planned', 0))
        date = request.POST.get('date', timezone.now().date())
        
        goal, created = DailyGoal.objects.get_or_create(
            user=request.user,
            date=date,
            defaults={'videos_planned': videos_planned}
        )
        
        if not created:
            goal.videos_planned = videos_planned
            goal.save()
        
        return JsonResponse({
            'success': True,
            'videos_planned': goal.videos_planned,
            'videos_completed': goal.videos_completed,
        })
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)
