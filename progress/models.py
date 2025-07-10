from django.db import models
from django.conf import settings
from django.utils import timezone

class LearningSession(models.Model):
    """Model to track individual learning sessions"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    videos_completed = models.IntegerField(default=0)
    total_duration = models.DurationField(null=True, blank=True)
    
    class Meta:
        ordering = ['-date', '-start_time']
    
    def __str__(self):
        return f"{self.user.email}'s session on {self.date}"
    
    def end_session(self):
        """End the current learning session"""
        self.end_time = timezone.now()
        self.total_duration = self.end_time - self.start_time
        self.save()

class LearningStreak(models.Model):
    """Model to track user's learning streaks"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.email}'s learning streak"
    
    def update_streak(self, activity_date):
        """Update the user's learning streak"""
        if self.last_activity_date:
            date_diff = (activity_date - self.last_activity_date).days
            
            if date_diff == 1:  # Consecutive day
                self.current_streak += 1
                self.longest_streak = max(self.current_streak, self.longest_streak)
            elif date_diff > 1:  # Streak broken
                self.current_streak = 1
            # If date_diff == 0, user is learning on the same day
            
        else:  # First time learning
            self.current_streak = 1
            self.longest_streak = 1
        
        self.last_activity_date = activity_date
        self.save()

class DailyGoal(models.Model):
    """Model to track daily learning goals"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField()
    videos_planned = models.IntegerField(default=0)
    videos_completed = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['user', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.user.email}'s goal for {self.date}"
    
    def update_progress(self, completed_count):
        """Update progress towards daily goal"""
        self.videos_completed = completed_count
        if self.videos_planned > 0:
            self.is_completed = self.videos_completed >= self.videos_planned
        else:
            self.is_completed = False
        self.save()
