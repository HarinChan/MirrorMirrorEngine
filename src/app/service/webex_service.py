import os
import requests
from datetime import datetime
import urllib.parse

class WebexService:
    BASE_URL = "https://webexapis.com/v1"
    
    def __init__(self):
        self.client_id = os.environ.get('WEBEX_CLIENT_ID')
        self.client_secret = os.environ.get('WEBEX_CLIENT_SECRET')
        self.redirect_uri = os.environ.get('WEBEX_REDIRECT_URI')
        
    def get_auth_url(self):
        """Generate the WebEx OAuth authorization URL"""
        if not self.client_id or not self.redirect_uri:
            print("WARNING: WebEx OAuth credentials not set")
            # Return dummy URL for dev testing if needed or empty
            return ""
            
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": "meeting:schedules_read meeting:schedules_write",
            "state": "random_state_string" # Should generate random state for security
        }
        return f"{self.BASE_URL}/authorize?{urllib.parse.urlencode(params)}"

    def exchange_code(self, code):
        """Exchange authorization code for access token"""
        url = f"{self.BASE_URL}/access_token"
        payload = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error exchanging WebEx code: {e}")
            raise e

    def refresh_access_token(self, refresh_token):
        """Get new access token using refresh token"""
        url = f"{self.BASE_URL}/access_token"
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error refreshing WebEx token: {e}")
            raise e

    def create_meeting(self, access_token, title, start_time: datetime, end_time: datetime, attendees=None):
        """
        Create a WebEx meeting using a specific user's access token.
        """
        if not access_token:
            raise ValueError("No access token provided")

        url = f"{self.BASE_URL}/meetings"
        
        payload = {
            "title": title,
            "start": start_time.strftime('%Y-%m-%dT%H:%M:%S'),
            "end": end_time.strftime('%Y-%m-%dT%H:%M:%S'),
            "enabledAutoRecordMeeting": False,
            "allowAnyUserToBeCoHost": True
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error creating WebEx meeting: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            raise e

    def delete_meeting(self, access_token, meeting_id):
        """
        Delete a WebEx meeting.
        """
        if not access_token:
            raise ValueError("No access token provided")

        url = f"{self.BASE_URL}/meetings/{meeting_id}"
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        try:
            response = requests.delete(url, headers=headers)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error deleting WebEx meeting: {e}")
            raise e

    def update_meeting(self, access_token, meeting_id, start_time: datetime, end_time: datetime):
        """
        Update a WebEx meeting (reschedule).
        """
        if not access_token:
            raise ValueError("No access token provided")

        url = f"{self.BASE_URL}/meetings/{meeting_id}"
        
        payload = {
            "start": start_time.strftime('%Y-%m-%dT%H:%M:%S'),
            "end": end_time.strftime('%Y-%m-%dT%H:%M:%S')
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.put(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error updating WebEx meeting: {e}")
            raise e
