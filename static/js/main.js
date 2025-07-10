// Progress Tracker Class
class ProgressTracker {
    constructor() {
        this.streakCounter = document.getElementById('streak-counter');
        this.progressCircles = document.querySelectorAll('.progress-circle');
        this.notificationToast = document.getElementById('notificationToast');
        this.notificationTitle = document.getElementById('notificationTitle');
        this.notificationMessage = document.getElementById('notificationMessage');
        this.learningTime = document.getElementById('learning-time');
        
        this.initializeNotifications();
        this.initializeProgressCircles();
        this.checkLearningTime();
    }

    // Initialize notification system
    initializeNotifications() {
        if ("Notification" in window) {
            Notification.requestPermission();
        }

        // Initialize Bootstrap toast
        if (this.notificationToast) {
            this.toast = new bootstrap.Toast(this.notificationToast, {
                autohide: true,
                delay: 5000
            });
        }
    }

    // Show notification
    showNotification(title, message, type = 'info') {
        // Browser notification
        if (Notification.permission === "granted") {
            new Notification(title, {
                body: message,
                icon: '/static/img/logo.png'
            });
        }

        // In-app toast notification
        if (this.notificationToast) {
            this.notificationTitle.textContent = title;
            this.notificationMessage.textContent = message;
            this.notificationToast.className = `toast border-${type}`;
            this.toast.show();
        }
    }

    // Initialize progress circles
    initializeProgressCircles() {
        this.progressCircles.forEach(circle => {
            const progress = circle.dataset.progress;
            circle.style.setProperty('--progress', `${progress}%`);
        });
    }

    // Load and update streak
    async loadStreak() {
        if (!this.streakCounter) return;

        try {
            const response = await fetch('/api/users/streak/');
            if (response.ok) {
                const data = await response.json();
                this.streakCounter.textContent = data.current_streak;
                
                if (data.streak_at_risk) {
                    this.showNotification(
                        'Streak at Risk!',
                        'Complete a video today to maintain your streak!',
                        'warning'
                    );
                }
            }
        } catch (error) {
            console.error('Error loading streak:', error);
        }
    }

    // Check learning time and send reminder
    checkLearningTime() {
        if (!this.learningTime) return;

        const preferredTime = this.learningTime.dataset.time;
        if (!preferredTime) return;

        // Parse preferred time
        const [hours, minutes] = preferredTime.split(':').map(Number);
        
        // Check time every minute
        setInterval(() => {
            const now = new Date();
            if (now.getHours() === hours && now.getMinutes() === minutes) {
                this.showNotification(
                    'Time to Learn!',
                    'It\'s your preferred learning time. Ready to continue your progress?',
                    'info'
                );
            }
        }, 60000);
    }

    // Update progress for a video
    async updateVideoProgress(videoId, completed) {
        try {
            const response = await fetch(`/api/videos/${videoId}/progress/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: JSON.stringify({ completed })
            });

            if (response.ok) {
                const data = await response.json();
                
                // Update UI
                this.updateProgressUI(data);
                
                // Show achievement notification
                if (data.achievement) {
                    this.showNotification(
                        'Achievement Unlocked!',
                        data.achievement,
                        'success'
                    );
                }
                
                return true;
            }
            return false;
        } catch (error) {
            console.error('Error updating progress:', error);
            return false;
        }
    }

    // Update UI elements after progress change
    updateProgressUI(data) {
        // Update streak counter if available
        if (this.streakCounter && data.current_streak) {
            this.streakCounter.textContent = data.current_streak;
        }

        // Update progress circles if available
        if (data.progress_percentage) {
            this.progressCircles.forEach(circle => {
                circle.style.setProperty('--progress', `${data.progress_percentage}%`);
                const textElement = circle.querySelector('.progress-text');
                if (textElement) {
                    textElement.textContent = `${Math.round(data.progress_percentage)}%`;
                }
            });
        }
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    window.progressTracker = new ProgressTracker();
});

// Handle form validation
document.querySelectorAll('form.needs-validation').forEach(form => {
    form.addEventListener('submit', event => {
        if (!form.checkValidity()) {
            event.preventDefault();
            event.stopPropagation();
        }
        form.classList.add('was-validated');
    });
});

// Handle video completion buttons
document.querySelectorAll('.mark-complete').forEach(button => {
    button.addEventListener('click', async function() {
        const videoId = this.dataset.videoId;
        try {
            // Get CSRF token
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            
            // Make the request to mark video as complete
            const response = await fetch(`/playlists/video/${videoId}/complete/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error('Failed to mark video as completed');
            }

            const data = await response.json();
            if (data.success) {
                // Update button state
                this.disabled = true;
                this.innerHTML = '<i class="fas fa-check"></i> Completed';
                this.classList.replace('btn-success', 'btn-secondary');

                // Update progress bar if it exists
                const progressBar = document.querySelector('.progress-bar');
                if (progressBar) {
                    progressBar.style.width = `${data.progress}%`;
                    progressBar.setAttribute('aria-valuenow', data.progress);
                    progressBar.textContent = `${Math.round(data.progress)}%`;
                }

                // Update completion count
                const completionCount = document.querySelector('.completion-count');
                if (completionCount) {
                    completionCount.textContent = data.completed_count;
                }

                // Update daily goal progress
                const dailyGoalProgress = document.querySelector('.progress-bar');
                if (dailyGoalProgress) {
                    const videosPlanned = data.videos_planned || parseInt(dailyGoalProgress.getAttribute('aria-valuemax'));
                    const newProgress = videosPlanned > 0 ? (data.videos_completed_today / videosPlanned) * 100 : 0;
                    dailyGoalProgress.style.width = `${newProgress}%`;
                    dailyGoalProgress.setAttribute('aria-valuenow', data.videos_completed_today);
                }

                // Update videos completed today text
                const videosCompletedText = document.querySelector('.mb-4');
                if (videosCompletedText) {
                    const videosPlanned = data.videos_planned || parseInt(dailyGoalProgress.getAttribute('aria-valuemax'));
                    videosCompletedText.textContent = `Completed ${data.videos_completed_today} of ${videosPlanned} videos today`;
                }

                // Update stat card for videos completed today
                const statNumber = document.querySelector('.stat-number');
                if (statNumber) {
                    statNumber.textContent = data.videos_completed_today;
                }

                // Update video item appearance
                const videoItem = this.closest('.video-item');
                if (videoItem) {
                    videoItem.classList.add('completed');
                    const completionDate = videoItem.querySelector('.completion-date');
                    if (completionDate) {
                        completionDate.textContent = `Completed on ${data.completion_date}`;
                    }
                }

                // Show success notification
                showNotification('Success', 'Video marked as completed!', 'success');
            }
        } catch (error) {
            console.error('Error:', error);
            showNotification('Error', 'Failed to mark video as completed', 'danger');
        }
    });
}); 