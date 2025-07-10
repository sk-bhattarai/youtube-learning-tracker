# YouTube Learning Progress Tracker

A full-stack web application that helps users track their learning progress through YouTube playlists. Users can import playlists, set learning durations, track progress with interactive charts, and receive browser notifications for their learning schedule.

## Features

- Import YouTube playlists via URL
- Choose custom learning duration (30/60/90 days)
- Auto-divide videos into daily tasks
- Track progress with interactive pie charts
- Daily learning streak counter
- Browser notifications for learning reminders
- Direct YouTube video playback

## Tech Stack

- Backend: Django
- Frontend: HTML, CSS, JavaScript
- Charts: Chart.js
- Notifications: Browser Notifications API
- YouTube Data Integration: YouTube Data API v3
- Database: SQLite
- Styling: Bootstrap 4

## Setup Instructions

1. Install Python 3.8 or higher
2. Clone this repository
3. Create a virtual environment:
   ```bash
   python -m venv venv
   ```
4. Activate the virtual environment:
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - Unix/MacOS:
     ```bash
     source venv/bin/activate
     ```
5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
6. Set up environment variables:
   - Create a `.env` file in the root directory
   - Add your YouTube API key:
     ```
     YOUTUBE_API_KEY=your_api_key_here
     ```
7. Run migrations:
   ```bash
   python manage.py migrate
   ```
8. Start the development server:
   ```bash
   python manage.py runserver
   ```

## Getting a YouTube API Key

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the YouTube Data API v3
4. Create credentials (API key)
5. Add the API key to your `.env` file

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see the LICENSE file for details. 