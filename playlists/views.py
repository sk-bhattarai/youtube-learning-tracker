from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from .models import Playlist, Video
from progress.models import DailyGoal, LearningStreak
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import isodate
from datetime import timedelta
import logging
import json

logger = logging.getLogger(__name__)

def get_youtube_service():
    """Create YouTube API service object"""
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        logger.error("YouTube API key not found in environment variables")
        raise ValueError("YouTube API key not configured")
    return build('youtube', 'v3', developerKey=api_key)

@login_required
def playlist_list(request):
    """Display user's playlists"""
    playlists = Playlist.objects.filter(user=request.user)
    return render(request, 'playlists/playlist_list.html', {'playlists': playlists})

@login_required
def test_youtube_api(request):
    """Test YouTube API connection"""
    try:
        youtube = get_youtube_service()
        # Try to fetch a sample playlist
        playlist_response = youtube.playlists().list(
            part='snippet',
            id='PLillGF-RfqbYhQsN5WMXy6VsDMKGadrJ-'  # Sample playlist ID
        ).execute()
        
        return JsonResponse({
            'success': True,
            'message': 'YouTube API connection successful',
            'api_response': playlist_response
        })
    except Exception as e:
        logger.error(f"YouTube API test error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def add_playlist(request):
    """Add a new playlist"""
    if request.method == 'POST':
        playlist_url = request.POST.get('playlist_url')
        target_days = int(request.POST.get('target_days', 30))
        
        try:
            # Extract playlist ID from URL
            if 'list=' not in playlist_url:
                messages.error(request, 'Invalid playlist URL. Please provide a valid YouTube playlist URL.')
                return redirect('playlists:add_playlist')
            
            playlist_id = playlist_url.split('list=')[-1].split('&')[0]
            logger.info(f"Attempting to fetch playlist ID: {playlist_id}")
            
            # Get playlist details from YouTube API
            youtube = get_youtube_service()
            
            try:
                # Get playlist details
                playlist_response = youtube.playlists().list(
                    part='snippet',
                    id=playlist_id
                ).execute()
                
                if not playlist_response.get('items'):
                    messages.error(request, 'Playlist not found or is private.')
                    logger.error(f"No items found for playlist ID: {playlist_id}")
                    return redirect('playlists:add_playlist')
                
                playlist_data = playlist_response['items'][0]['snippet']
                logger.info(f"Successfully fetched playlist: {playlist_data['title']}")
                
                # Create playlist
                playlist = Playlist.objects.create(
                    user=request.user,
                    youtube_id=playlist_id,
                    title=playlist_data['title'],
                    description=playlist_data['description'],
                    thumbnail_url=playlist_data['thumbnails']['high']['url'],
                    target_completion_days=target_days,
                    start_date=timezone.now().date()
                )
                
                # Get playlist items with pagination
                videos = []
                next_page_token = None
                total_duration = timedelta()
                
                while True:
                    try:
                        # Get videos in playlist
                        playlist_items = youtube.playlistItems().list(
                            part='snippet,contentDetails',
                            playlistId=playlist_id,
                            maxResults=50,
                            pageToken=next_page_token
                        ).execute()
                        
                        if not playlist_items.get('items'):
                            logger.warning(f"No videos found in playlist: {playlist_id}")
                            break
                        
                        # Get video durations in batches
                        video_ids = [item['contentDetails']['videoId'] for item in playlist_items['items']]
                        logger.info(f"Fetching details for {len(video_ids)} videos")
                        
                        video_response = youtube.videos().list(
                            part='contentDetails',
                            id=','.join(video_ids)
                        ).execute()
                        
                        # Create video objects
                        for item, video_details in zip(playlist_items['items'], video_response['items']):
                            try:
                                duration = isodate.parse_duration(video_details['contentDetails']['duration'])
                                total_duration += duration
                                
                                video = Video(
                                    playlist=playlist,
                                    youtube_id=item['contentDetails']['videoId'],
                                    title=item['snippet']['title'],
                                    description=item['snippet'].get('description', ''),
                                    thumbnail_url=item['snippet']['thumbnails']['high']['url'],
                                    duration=duration,
                                    position=len(videos)
                                )
                                videos.append(video)
                                logger.info(f"Added video: {video.title}")
                            except (KeyError, ValueError) as e:
                                logger.error(f"Error processing video: {str(e)}")
                                continue
                        
                        next_page_token = playlist_items.get('nextPageToken')
                        if not next_page_token:
                            break
                            
                    except HttpError as e:
                        logger.error(f"YouTube API error while fetching videos: {str(e)}")
                        if e.resp.status in [403, 429]:
                            messages.warning(request, 'Some videos could not be fetched due to API limits. Please try again later.')
                            break
                        raise
                
                if not videos:
                    playlist.delete()
                    messages.error(request, 'No valid videos found in the playlist.')
                    return redirect('playlists:add_playlist')
                
                # Bulk create videos
                Video.objects.bulk_create(videos)
                
                # Update video count and save
                playlist.video_count = len(videos)
                playlist.save()
                
                messages.success(request, f'Successfully imported {len(videos)} videos from the playlist!')
                return redirect('playlists:playlist_detail', pk=playlist.pk)
                
            except HttpError as e:
                logger.error(f"YouTube API error: {str(e)}")
                if e.resp.status in [403, 429]:
                    messages.error(request, 'YouTube API quota exceeded. Please try again later.')
                elif e.resp.status == 404:
                    messages.error(request, 'Playlist not found.')
                else:
                    messages.error(request, f'Error accessing YouTube API: {str(e)}')
                return redirect('playlists:add_playlist')
                
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            messages.error(request, f'An unexpected error occurred: {str(e)}')
            return redirect('playlists:add_playlist')
    
    return render(request, 'playlists/add_playlist.html')

@login_required
def playlist_detail(request, pk):
    """Display playlist details and videos"""
    playlist = get_object_or_404(Playlist, pk=pk, user=request.user)
    
    try:
        # Get all videos
        videos = playlist.video_set.all().order_by('position')
        
        # Calculate overall progress
        progress = playlist.get_progress_percentage()
        completed_videos = videos.filter(is_completed=True)
        remaining_videos = videos.exclude(is_completed=True)
        
        # Calculate duration-based progress
        total_duration = playlist.get_total_duration()
        completed_duration = playlist.get_completed_duration()
        duration_progress = 0
        if total_duration:
            duration_progress = (completed_duration.total_seconds() / total_duration.total_seconds()) * 100
        
        # Get today's schedule
        today = timezone.now().date()
        todays_videos = playlist.get_videos_for_day(today)
        
        # Calculate daily target duration
        daily_target_duration = timedelta()
        if total_duration:
            daily_target_duration = total_duration / playlist.target_completion_days
        
        # Get completion status for today's videos
        todays_completed = sum(1 for video in todays_videos if video.is_completed)
        todays_total = len(todays_videos)
        
        # Calculate estimated completion date
        estimated_completion = None
        if remaining_videos.exists() and progress > 0:
            days_elapsed = (timezone.now().date() - playlist.start_date).days
            if days_elapsed > 0:
                completion_rate = progress / days_elapsed
                if completion_rate > 0:
                    days_remaining = (100 - progress) / completion_rate
                    estimated_completion = timezone.now().date() + timedelta(days=days_remaining)
        
        # Get complete schedule
        daily_schedule = playlist.get_daily_schedule()
        
        context = {
            'playlist': playlist,
            'videos': videos,
            'progress': progress,
            'duration_progress': duration_progress,
            'todays_videos': todays_videos,
            'todays_completed': todays_completed,
            'todays_total': todays_total,
            'completed_count': completed_videos.count(),
            'total_count': videos.count(),
            'total_duration': total_duration,
            'completed_duration': completed_duration,
            'daily_target_duration': daily_target_duration,
            'estimated_completion': estimated_completion,
            'daily_schedule': daily_schedule,
        }
        
        return render(request, 'playlists/playlist_detail.html', context)
        
    except Exception as e:
        logger.error(f"Error in playlist detail view: {str(e)}")
        messages.error(request, 'An error occurred while loading the playlist.')
        return redirect('playlists:playlist_list')

@login_required
def playlist_edit(request, pk):
    """Edit playlist settings"""
    playlist = get_object_or_404(Playlist, pk=pk, user=request.user)
    
    if request.method == 'POST':
        target_days = int(request.POST.get('target_days', 30))
        playlist.target_completion_days = target_days
        playlist.save()
        
        messages.success(request, 'Playlist settings updated successfully!')
        return redirect('playlists:playlist_detail', pk=playlist.pk)
    
    return render(request, 'playlists/playlist_edit.html', {'playlist': playlist})

@login_required
def playlist_delete(request, pk):
    """Delete a playlist"""
    playlist = get_object_or_404(Playlist, pk=pk, user=request.user)
    
    if request.method == 'POST':
        playlist.delete()
        messages.success(request, 'Playlist deleted successfully!')
        return redirect('playlists:playlist_list')
    
    return render(request, 'playlists/playlist_delete.html', {'playlist': playlist})

@login_required
def import_playlist(request):
    """API endpoint for importing playlist"""
    if request.method == 'POST':
        playlist_url = request.POST.get('playlist_url')
        if not playlist_url:
            return JsonResponse({'error': 'Playlist URL is required'}, status=400)
        
        # Extract playlist ID and import
        # ... (similar to add_playlist logic)
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def fetch_playlist_info(request):
    """Fetch playlist information from YouTube API"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        playlist_url = data.get('url')
        
        if not playlist_url or 'list=' not in playlist_url:
            return JsonResponse({'error': 'Invalid playlist URL'}, status=400)
        
        playlist_id = playlist_url.split('list=')[-1].split('&')[0]
        youtube = get_youtube_service()
        
        # Get playlist details
        playlist_response = youtube.playlists().list(
            part='snippet',
            id=playlist_id
        ).execute()
        
        if not playlist_response.get('items'):
            return JsonResponse({'error': 'Playlist not found or is private'}, status=404)
        
        playlist_data = playlist_response['items'][0]['snippet']
        
        # Get first page of videos to count them
        playlist_items = youtube.playlistItems().list(
            part='snippet,contentDetails',
            playlistId=playlist_id,
            maxResults=50
        ).execute()
        
        video_count = playlist_items['pageInfo']['totalResults']
        
        # Get duration of first batch of videos
        if playlist_items.get('items'):
            video_ids = [item['contentDetails']['videoId'] for item in playlist_items['items']]
            video_response = youtube.videos().list(
                part='contentDetails',
                id=','.join(video_ids)
            ).execute()
            
            total_duration = timedelta()
            for video in video_response.get('items', []):
                duration = isodate.parse_duration(video['contentDetails']['duration'])
                total_duration += duration
            
            # Estimate total duration based on first batch
            avg_duration = total_duration / len(video_response['items'])
            estimated_total_duration = avg_duration * video_count
            
            hours = int(estimated_total_duration.total_seconds() // 3600)
            minutes = int((estimated_total_duration.total_seconds() % 3600) // 60)
            duration_str = f"{hours}h {minutes}m"
        else:
            duration_str = "Unknown duration"
        
        return JsonResponse({
            'title': playlist_data['title'],
            'description': playlist_data['description'],
            'thumbnail_url': playlist_data['thumbnails']['high']['url'],
            'video_count': video_count,
            'total_duration': duration_str
        })
        
    except HttpError as e:
        logger.error(f"YouTube API error: {str(e)}")
        if e.resp.status in [403, 429]:
            return JsonResponse({'error': 'YouTube API quota exceeded'}, status=429)
        return JsonResponse({'error': str(e)}, status=500)
        
    except Exception as e:
        logger.error(f"Error fetching playlist info: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

@login_required
def get_user_streak(request):
    """Get user's current learning streak"""
    try:
        # Get user's completed videos in the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        completed_videos = Video.objects.filter(
            playlist__user=request.user,
            completed_at__gte=thirty_days_ago
        ).order_by('completed_at')
        
        if not completed_videos:
            return JsonResponse({
                'current_streak': 0,
                'longest_streak': 0,
                'total_completed': 0
            })
        
        # Calculate current streak
        current_streak = 0
        longest_streak = 0
        current_date = timezone.now().date()
        
        # Group completed videos by date
        completion_dates = set()
        for video in completed_videos:
            completion_dates.add(video.completed_at.date())
        
        # Calculate current streak
        while current_date in completion_dates:
            current_streak += 1
            current_date -= timedelta(days=1)
        
        # Calculate longest streak
        temp_streak = 0
        dates_list = sorted(list(completion_dates), reverse=True)
        
        for i in range(len(dates_list)):
            if i == 0 or (dates_list[i-1] - dates_list[i]).days == 1:
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
            else:
                temp_streak = 1
        
        return JsonResponse({
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'total_completed': len(completed_videos)
        })
        
    except Exception as e:
        logger.error(f"Error calculating user streak: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

@login_required
def update_video_progress(request, video_id):
    """Mark a video as completed"""
    if request.method == 'POST':
        try:
            video = get_object_or_404(Video, id=video_id, playlist__user=request.user)
            video.mark_completed()
            
            # Calculate new progress
            playlist = video.playlist
            progress = playlist.get_progress_percentage()
            completed_count = playlist.video_set.filter(is_completed=True).count()
            
            # Get today's completion count
            today = timezone.now().date()
            videos_completed_today = Video.objects.filter(
                playlist__user=request.user,
                is_completed=True,
                completed_at__date=today
            ).count()
            
            # Update daily goal
            daily_goal, created = DailyGoal.objects.get_or_create(
                user=request.user,
                date=today,
                defaults={'videos_planned': 0}
            )
            daily_goal.update_progress(videos_completed_today)
            
            return JsonResponse({
                'success': True,
                'progress': progress,
                'completed_count': completed_count,
                'videos_completed_today': videos_completed_today,
                'videos_planned': daily_goal.videos_planned,
                'completion_date': video.completed_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        except Exception as e:
            logger.error(f"Error updating video progress: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})
