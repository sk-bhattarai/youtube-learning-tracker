from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class CustomUser(AbstractUser):
    email = models.EmailField(_('email address'), unique=True)
    preferred_learning_time = models.TimeField(null=True, blank=True)
    notification_enabled = models.BooleanField(default=True)
    streak_count = models.IntegerField(default=0)
    last_learning_date = models.DateField(null=True, blank=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email
        
    def update_streak(self, current_date):
        if self.last_learning_date:
            date_diff = (current_date - self.last_learning_date).days
            
            if date_diff == 1:
                self.streak_count += 1
            elif date_diff > 1:
                self.streak_count = 1
            
        else:
            self.streak_count = 1
            
        self.last_learning_date = current_date
        self.save()
