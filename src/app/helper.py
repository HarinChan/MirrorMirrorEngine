import socket
import re
from typing import List, Dict, Optional
from datetime import datetime, timezone


class PenpalsHelper:
    """Static helper class for PenPals application utilities"""
    
    @staticmethod
    def find_open_port(start_port: int = 5000, end_port: int = 6000) -> int:
        """
        Find an available port in the given range.
        
        Args:
            start_port: Starting port number (inclusive)
            end_port: Ending port number (exclusive)
            
        Returns:
            Available port number, or -1 if none found
        """
        for port in range(start_port, end_port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('127.0.0.1', port)) != 0:
                    return port
        return -1
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email format using regex.
        
        Args:
            email: Email string to validate
            
        Returns:
            True if email format is valid, False otherwise
        """
        if not email or not isinstance(email, str):
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_coordinates(latitude: Optional[str], longitude: Optional[str]) -> bool:
        """
        Validate latitude and longitude coordinates.
        
        Args:
            latitude: Latitude as string
            longitude: Longitude as string
            
        Returns:
            True if coordinates are valid, False otherwise
        """
        if not latitude or not longitude:
            return True  # Optional fields
        
        try:
            lat = float(latitude)
            lng = float(longitude)
            return -90 <= lat <= 90 and -180 <= lng <= 180
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def sanitize_interests(interests: List[str]) -> List[str]:
        """
        Sanitize and normalize interest strings.
        
        Args:
            interests: List of interest strings
            
        Returns:
            Cleaned list of interests
        """
        if not interests or not isinstance(interests, list):
            return []
        
        sanitized = []
        for interest in interests:
            if isinstance(interest, str):
                # Strip whitespace, convert to lowercase, remove extra spaces
                clean_interest = ' '.join(interest.strip().lower().split())
                if clean_interest and len(clean_interest) <= 50:  # Max length check
                    sanitized.append(clean_interest)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_interests = []
        for interest in sanitized:
            if interest not in seen:
                seen.add(interest)
                unique_interests.append(interest)
        
        return unique_interests[:10]  # Limit to 10 interests
    
    @staticmethod
    def format_profile_response(classroom, include_friends: bool = False) -> Dict:
        """
        Format classroom data for API responses.
        
        Args:
            classroom: Profile/Classroom model instance
            include_friends: Whether to include friends list
            
        Returns:
            Formatted classroom dictionary
        """
        response = {
            "id": classroom.id,
            "name": classroom.name,
            "location": classroom.location,
            "latitude": classroom.lattitude,  # Keep original typo for consistency
            "longitude": classroom.longitude,
            "class_size": classroom.class_size,
            "availability": classroom.availability,
            "interests": classroom.interests,
            "created_at": classroom.account.created_at.isoformat() if hasattr(classroom, 'account') else None
        }
        
        if include_friends:
            friends = []
            for relation in classroom.sent_relations:
                friend = relation.to_profile
                friends.append({
                    "id": friend.id,
                    "name": friend.name,
                    "location": friend.location,
                    "interests": friend.interests,
                    "friends_since": relation.created_at.isoformat()
                })
            response["friends"] = friends
            response["friends_count"] = len(friends)
        
        return response
    
    @staticmethod
    def calculate_interest_similarity(interests1: List[str], interests2: List[str]) -> float:
        """
        Calculate similarity between two interest lists using Jaccard similarity.
        
        Args:
            interests1: First list of interests
            interests2: Second list of interests
            
        Returns:
            Similarity score between 0 and 1
        """
        if not interests1 or not interests2:
            return 0.0
        
        set1 = set(interest.lower().strip() for interest in interests1)
        set2 = set(interest.lower().strip() for interest in interests2)
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    @staticmethod
    def get_current_utc_timestamp() -> datetime:
        """
        Get current UTC timestamp.
        
        Returns:
            Current datetime in UTC timezone
        """
        return datetime.now(timezone.utc)
    
    @staticmethod
    def validate_availability_format(availability: Optional[List]) -> bool:
        """
        Validate availability format (should be list of time slots).
        
        Args:
            availability: Availability data to validate
            
        Returns:
            True if format is valid, False otherwise
        """
        if availability is None:
            return True  # Optional field
        
        if not isinstance(availability, list):
            return False
        
        # Each availability item should be a dict with day and time info
        for slot in availability:
            if not isinstance(slot, dict):
                return False
            # Basic validation - could be enhanced based on specific format requirements
            if 'day' not in slot or 'time' not in slot:
                return False
        
        return True