from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

class Playlist(models.Model):
    """Model to store YouTube playlist information"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    youtube_id = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    thumbnail_url = models.URLField()
    video_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    target_completion_days = models.IntegerField(default=30)
    start_date = models.DateField(default=timezone.now)
    
    def __str__(self):
        return self.title
    
    def get_progress_percentage(self):
        """Calculate the percentage of completed videos"""
        completed_count = self.video_set.filter(is_completed=True).count()
        if self.video_count == 0:
            return 0
        return (completed_count / self.video_count) * 100
    
    def get_total_duration(self):
        """Get total duration of all videos in the playlist"""
        return sum((video.duration for video in self.video_set.all()), timedelta())
    
    def get_completed_duration(self):
        """Get total duration of completed videos"""
        return sum((video.duration for video in self.video_set.filter(is_completed=True)), timedelta())
    
    def get_videos_for_day(self, target_date):
        """Get the list of videos scheduled for a specific date"""
        if not self.video_count:
            return []
            
        # Get all videos ordered by position
        all_videos = list(self.video_set.all().order_by('position'))
        if not all_videos:
            return []
            
        # Calculate total duration and average duration per day
        total_duration = self.get_total_duration()
        avg_duration_per_day = total_duration / self.target_completion_days
        
        # Get completed videos
        completed_videos = set(self.video_set.filter(is_completed=True).values_list('id', flat=True))
        
        # Calculate which day we're on
        days_from_start = (target_date - self.start_date).days
        if days_from_start < 0:
            return []
            
        # Calculate target duration for all days up to target_date
        target_duration = avg_duration_per_day * (days_from_start + 1)
        
        # Find videos that should be watched by target_date
        current_duration = timedelta()
        videos_for_today = []
        
        for video in all_videos:
            if video.id in completed_videos:
                current_duration += video.duration
                continue
                
            if current_duration < target_duration:
                videos_for_today.append(video)
                current_duration += video.duration
            else:
                break
        
        return videos_for_today
    
    def get_daily_schedule(self):
        """Get a complete schedule of videos across all days"""
        all_videos = list(self.video_set.all().order_by('position'))
        if not all_videos:
            return {}
            
        total_duration = self.get_total_duration()
        avg_duration_per_day = total_duration / self.target_completion_days
        
        schedule = {}
        current_day = 0
        current_duration = timedelta()
        current_day_videos = []
        
        for video in all_videos:
            current_day_videos.append(video)
            current_duration += video.duration
            
            if current_duration >= avg_duration_per_day:
                schedule[current_day] = current_day_videos
                current_day += 1
                current_duration = timedelta()
                current_day_videos = []
        
        # Add remaining videos to the last day
        if current_day_videos:
            schedule[current_day] = current_day_videos
        
        return schedule

class Video(models.Model):
    """Model to store individual video information from the playlist"""
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE)
    youtube_id = models.CharField(max_length=100)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    thumbnail_url = models.URLField()
    duration = models.DurationField()
    position = models.IntegerField()  # Position in playlist
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['position']
    
    def __str__(self):
        return self.title
    
    def mark_completed(self):
        """Mark the video as completed"""
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save()
        
        # Update user streak
        self.playlist.user.update_streak(timezone.now().date())
