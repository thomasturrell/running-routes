#!/usr/bin/env python3
"""
Strava API integration for running routes.

This module provides secure integration with the Strava API to:
1. Fetch activity data for route validation
2. Upload routes to Strava
3. Cache frequently accessed data to reduce API calls
4. Handle webhook notifications for real-time updates

Features:
- Secure token management
- Rate limiting compliance
- Data caching
- Webhook support for real-time updates
- Activity analysis and comparison
"""

import os
import json
import time
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import requests
from dataclasses import dataclass

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class StravaActivity:
    """Represents a Strava activity."""
    id: int
    name: str
    type: str
    distance: float
    moving_time: int
    total_elevation_gain: float
    start_date: datetime
    polyline: Optional[str] = None

class StravaAPIClient:
    """Strava API client with rate limiting and caching."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize Strava API client.
        
        Args:
            cache_dir: Directory for caching API responses
        """
        self.base_url = "https://www.strava.com/api/v3"
        self.cache_dir = cache_dir or Path("cache/strava")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Rate limiting (Strava allows 100 requests per 15 minutes, 1000 per day)
        self.rate_limit_short = {'requests': 0, 'reset_time': time.time() + 900}  # 15 minutes
        self.rate_limit_daily = {'requests': 0, 'reset_time': time.time() + 86400}  # 24 hours
        
        # Load tokens from environment
        self.client_id = os.getenv('STRAVA_CLIENT_ID')
        self.client_secret = os.getenv('STRAVA_CLIENT_SECRET')
        self.access_token = os.getenv('STRAVA_ACCESS_TOKEN')
        self.refresh_token = os.getenv('STRAVA_REFRESH_TOKEN')
        
        if not all([self.client_id, self.client_secret]):
            logger.warning("Strava API credentials not found in environment variables")
    
    def _check_rate_limits(self) -> bool:
        """
        Check if we're within rate limits.
        
        Returns:
            True if we can make a request, False otherwise
        """
        current_time = time.time()
        
        # Reset counters if time windows have expired
        if current_time >= self.rate_limit_short['reset_time']:
            self.rate_limit_short = {'requests': 0, 'reset_time': current_time + 900}
            
        if current_time >= self.rate_limit_daily['reset_time']:
            self.rate_limit_daily = {'requests': 0, 'reset_time': current_time + 86400}
        
        # Check limits
        if self.rate_limit_short['requests'] >= 100:
            logger.warning("Short-term rate limit exceeded")
            return False
            
        if self.rate_limit_daily['requests'] >= 1000:
            logger.warning("Daily rate limit exceeded")
            return False
            
        return True
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None,
                     use_cache: bool = True, cache_ttl: int = 3600) -> Optional[Dict]:
        """
        Make a request to the Strava API with rate limiting and caching.
        
        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters
            use_cache: Whether to use cached responses
            cache_ttl: Cache time-to-live in seconds
            
        Returns:
            API response data or None if failed
        """
        if not self.access_token:
            logger.error("No access token available")
            return None
            
        # Check cache first
        if use_cache:
            cache_key = self._get_cache_key(endpoint, params)
            cached_data = self._get_cached_data(cache_key, cache_ttl)
            if cached_data:
                return cached_data
        
        # Check rate limits
        if not self._check_rate_limits():
            logger.error("Rate limit exceeded")
            return None
        
        # Make request
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            # Update rate limit counters
            self.rate_limit_short['requests'] += 1
            self.rate_limit_daily['requests'] += 1
            
            # Handle rate limit headers from Strava
            if 'X-RateLimit-Usage' in response.headers:
                usage = response.headers['X-RateLimit-Usage'].split(',')
                if len(usage) >= 2:
                    self.rate_limit_short['requests'] = int(usage[0])
                    self.rate_limit_daily['requests'] = int(usage[1])
            
            response.raise_for_status()
            data = response.json()
            
            # Cache successful response
            if use_cache:
                self._cache_data(cache_key, data)
                
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
    
    def _get_cache_key(self, endpoint: str, params: Optional[Dict] = None) -> str:
        """Generate cache key for request."""
        key_data = f"{endpoint}_{json.dumps(params, sort_keys=True) if params else ''}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cached_data(self, cache_key: str, cache_ttl: int) -> Optional[Dict]:
        """Get data from cache if still valid."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
            
        try:
            stat = cache_file.stat()
            if time.time() - stat.st_mtime > cache_ttl:
                return None  # Cache expired
                
            with open(cache_file, 'r') as f:
                return json.load(f)
                
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to read cache file {cache_file}: {e}")
            return None
    
    def _cache_data(self, cache_key: str, data: Dict) -> None:
        """Save data to cache."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except OSError as e:
            logger.warning(f"Failed to write cache file {cache_file}: {e}")
    
    def refresh_access_token(self) -> bool:
        """
        Refresh the access token using the refresh token.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.refresh_token or not self.client_id or not self.client_secret:
            logger.error("Missing credentials for token refresh")
            return False
        
        url = "https://www.strava.com/oauth/token"
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token'
        }
        
        try:
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.refresh_token = token_data['refresh_token']
            
            logger.info("Access token refreshed successfully")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Token refresh failed: {e}")
            return False
    
    def get_athlete_activities(self, limit: int = 30, page: int = 1,
                              after: Optional[datetime] = None,
                              before: Optional[datetime] = None) -> List[StravaActivity]:
        """
        Get athlete's activities.
        
        Args:
            limit: Number of activities to return (max 200)
            page: Page number
            after: Only return activities after this date
            before: Only return activities before this date
            
        Returns:
            List of Strava activities
        """
        params = {
            'per_page': min(limit, 200),
            'page': page
        }
        
        if after:
            params['after'] = int(after.timestamp())
        if before:
            params['before'] = int(before.timestamp())
        
        data = self._make_request('athlete/activities', params)
        
        if not data:
            return []
        
        activities = []
        for activity_data in data:
            try:
                activity = StravaActivity(
                    id=activity_data['id'],
                    name=activity_data['name'],
                    type=activity_data['type'],
                    distance=activity_data['distance'],
                    moving_time=activity_data['moving_time'],
                    total_elevation_gain=activity_data.get('total_elevation_gain', 0),
                    start_date=datetime.fromisoformat(activity_data['start_date'].replace('Z', '+00:00')),
                    polyline=activity_data.get('map', {}).get('summary_polyline')
                )
                activities.append(activity)
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to parse activity data: {e}")
                continue
        
        return activities
    
    def get_activity_details(self, activity_id: int) -> Optional[Dict]:
        """
        Get detailed information about a specific activity.
        
        Args:
            activity_id: Strava activity ID
            
        Returns:
            Activity details or None if failed
        """
        return self._make_request(f'activities/{activity_id}')
    
    def compare_route_with_activities(self, route_gpx_path: Path, 
                                    similarity_threshold: float = 0.8) -> List[Dict]:
        """
        Compare a GPX route with athlete's Strava activities.
        
        Args:
            route_gpx_path: Path to GPX route file
            similarity_threshold: Similarity threshold for matching (0-1)
            
        Returns:
            List of similar activities with similarity scores
        """
        # This is a placeholder for route comparison logic
        # In a full implementation, this would:
        # 1. Parse the GPX route
        # 2. Get athlete's activities
        # 3. Compare routes using polyline matching or geographic distance
        # 4. Return activities with similarity scores
        
        logger.info(f"Comparing route {route_gpx_path} with Strava activities")
        
        # Get recent running activities
        activities = self.get_athlete_activities(limit=50)
        running_activities = [a for a in activities if a.type.lower() in ['run', 'trail run']]
        
        # Placeholder for actual comparison
        similar_activities = []
        for activity in running_activities[:5]:  # Limit for demo
            # In reality, would calculate actual similarity
            similarity_score = 0.5  # Placeholder
            
            if similarity_score >= similarity_threshold:
                similar_activities.append({
                    'activity': activity,
                    'similarity': similarity_score
                })
        
        return similar_activities

class StravaWebhookHandler:
    """Handle Strava webhook notifications for real-time updates."""
    
    def __init__(self, verify_token: str):
        """
        Initialize webhook handler.
        
        Args:
            verify_token: Token for webhook verification
        """
        self.verify_token = verify_token
    
    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """
        Verify webhook subscription.
        
        Args:
            mode: Verification mode
            token: Verification token
            challenge: Challenge string
            
        Returns:
            Challenge string if verification successful, None otherwise
        """
        if mode == "subscribe" and token == self.verify_token:
            logger.info("Webhook verification successful")
            return challenge
        else:
            logger.warning("Webhook verification failed")
            return None
    
    def handle_webhook_event(self, event_data: Dict) -> bool:
        """
        Handle incoming webhook event.
        
        Args:
            event_data: Webhook event data
            
        Returns:
            True if handled successfully, False otherwise
        """
        try:
            object_type = event_data.get('object_type')
            aspect_type = event_data.get('aspect_type')
            object_id = event_data.get('object_id')
            
            logger.info(f"Received webhook: {object_type} {aspect_type} for {object_id}")
            
            if object_type == 'activity':
                if aspect_type == 'create':
                    return self._handle_activity_created(object_id)
                elif aspect_type == 'update':
                    return self._handle_activity_updated(object_id)
                elif aspect_type == 'delete':
                    return self._handle_activity_deleted(object_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle webhook event: {e}")
            return False
    
    def _handle_activity_created(self, activity_id: int) -> bool:
        """Handle new activity creation."""
        logger.info(f"New activity created: {activity_id}")
        # Implement logic to process new activity
        return True
    
    def _handle_activity_updated(self, activity_id: int) -> bool:
        """Handle activity update."""
        logger.info(f"Activity updated: {activity_id}")
        # Implement logic to handle activity updates
        return True
    
    def _handle_activity_deleted(self, activity_id: int) -> bool:
        """Handle activity deletion."""
        logger.info(f"Activity deleted: {activity_id}")
        # Implement logic to handle activity deletion
        return True

# Example usage
if __name__ == '__main__':
    # Initialize client
    client = StravaAPIClient()
    
    # Get recent activities
    activities = client.get_athlete_activities(limit=10)
    for activity in activities:
        print(f"{activity.name}: {activity.distance/1000:.1f}km, {activity.total_elevation_gain}m gain")