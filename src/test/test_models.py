"""
Unit tests for database models.
Tests model creation, relationships, constraints, and business logic.
"""

import pytest
from datetime import datetime
from werkzeug.security import check_password_hash
from sqlalchemy.exc import IntegrityError

from src.app.model.account import Account
from src.app.model.profile import Profile
from src.app.model.relation import Relation
from src.app.model.friendrequest import FriendRequest
from src.app.model.post import Post
from src.app.model.meeting import Meeting
from src.app.model.meetinginvitation import MeetingInvitation
from src.app.model.notification import Notification


@pytest.mark.unit
class TestAccountModel:
    """Tests for Account model."""
    
    def test_create_account(self, db, create_account):
        """Test basic account creation."""
        account = create_account(email='test@example.com', password='Password123!')
        
        assert account.id is not None
        assert account.email == 'test@example.com'
        assert account.password_hash is not None
        assert account.created_at is not None
    
    def test_email_uniqueness(self, db, create_account):
        """Test that email must be unique."""
        create_account(email='duplicate@example.com')
        
        with pytest.raises(IntegrityError):
            create_account(email='duplicate@example.com')
            db.session.commit()
    
    def test_password_hashing(self, db, create_account):
        """Test that passwords are hashed, not stored as plaintext."""
        password = 'MySecurePassword123!'
        account = create_account(email='hash@example.com', password=password)
        
        assert account.password_hash != password
        assert check_password_hash(account.password_hash, password)
        assert not check_password_hash(account.password_hash, 'WrongPassword')
    
    def test_check_password_method(self, db, create_account):
        """Test the check_password method if it exists."""
        account = create_account(email='method@example.com', password='TestPass123!')
        
        # If Account model has check_password method
        if hasattr(account, 'check_password'):
            assert account.check_password('TestPass123!')
            assert not account.check_password('WrongPassword')
    
    def test_webex_token_fields(self, db, create_account):
        """Test WebEx token storage fields."""
        account = create_account(email='webex@example.com')
        
        assert hasattr(account, 'webex_access_token')
        assert hasattr(account, 'webex_refresh_token')
        assert hasattr(account, 'webex_token_expires_at')
        
        # Set WebEx tokens
        account.webex_access_token = 'test_access_token'
        account.webex_refresh_token = 'test_refresh_token'
        account.webex_token_expires_at = datetime.utcnow()
        db.session.commit()
        
        assert account.webex_access_token == 'test_access_token'
    
    def test_account_profile_relationship(self, db, create_account, create_profile):
        """Test one-to-many relationship with profiles."""
        account = create_account(email='rel@example.com')
        profile1 = create_profile(account, name='Class 1')
        profile2 = create_profile(account, name='Class 2')
        
        #assert len(account.profiles) == 2
        assert profile1 in account.profiles
        assert profile2 in account.profiles
    
    def test_account_cascade_delete(self, db, create_account, create_profile):
        """Test that deleting account cascades to profiles."""
        account = create_account(email='cascade@example.com')
        profile = create_profile(account, name='Test Class')
        profile_id = profile.id
        
        db.session.delete(account)
        db.session.commit()
        
        # Profile should be deleted
        assert db.session.get(Profile, profile_id) is None


@pytest.mark.unit
class TestProfileModel:
    """Tests for Profile model."""
    
    def test_create_profile(self, db, create_account, create_profile):
        """Test basic profile creation."""
        account = create_account()
        profile = create_profile(account, name='Test Classroom', location='London')
        
        assert profile.id is not None
        assert profile.name == 'Test Classroom'
        assert profile.location == 'London'
        assert profile.account_id == account.id
    
    def test_coordinate_fields(self, db, create_account, create_profile):
        """Test latitude and longitude fields."""
        account = create_account()
        profile = create_profile(account, lattitude="51.5074", longitude="-0.1278")
        
        assert profile.lattitude == "51.5074"
        assert profile.longitude == "-0.1278"
    
    def test_interests_json_field(self, db, create_account, create_profile):
        """Test interests stored as JSON."""
        account = create_account()
        interests = ['coding', 'math', 'science']
        profile = create_profile(account, interests=interests)
        
        assert profile.interests == interests
        assert isinstance(profile.interests, list)
    
    def test_availability_json_field(self, db, create_account, create_profile):
        """Test availability stored as JSON."""
        account = create_account()
        availability = {'monday': '9-5', 'tuesday': '10-4'}
        profile = create_profile(account, availability=availability)
        
        assert profile.availability == availability
        assert isinstance(profile.availability, dict)
    
    def test_class_size_field(self, db, create_account, create_profile):
        """Test class size field."""
        account = create_account()
        profile = create_profile(account, class_size=25)
        
        assert profile.class_size == 25


@pytest.mark.unit
class TestRelationModel:
    """Tests for Relation model (friendships)."""
    
    def test_create_relation(self, db, create_account, create_profile, create_relation):
        """Test basic relation creation."""
        account = create_account()
        profile1 = create_profile(account, name='Class 1')
        profile2 = create_profile(account, name='Class 2')
        
        relation = create_relation(profile1, profile2, status='accepted')
        
        assert relation.id is not None
        assert relation.from_profile_id == profile1.id
        assert relation.to_profile_id == profile2.id
        assert relation.status == 'accepted'
    
    def test_relation_status_values(self, db, create_account, create_profile, create_relation):
        """Test different status values."""
        account = create_account()
        profile1 = create_profile(account, name='Class 1')
        profile2 = create_profile(account, name='Class 2')
        
        # Test pending
        rel_pending = create_relation(profile1, profile2, status='pending')
        assert rel_pending.status == 'pending'
    
    def test_unique_constraint(self, db, create_account, create_profile, create_relation):
        """Test unique constraint on (from_profile_id, to_profile_id)."""
        account = create_account()
        profile1 = create_profile(account, name='Class 1')
        profile2 = create_profile(account, name='Class 2')
        
        create_relation(profile1, profile2)
        
        # Attempting to create duplicate should fail
        with pytest.raises(IntegrityError):
            create_relation(profile1, profile2)
            db.session.commit()
    
    def test_bidirectional_relations(self, db, create_account, create_profile, create_relation):
        """Test that bidirectional relations require two records."""
        account = create_account()
        profile1 = create_profile(account, name='Class 1')
        profile2 = create_profile(account, name='Class 2')
        
        # Create A -> B
        create_relation(profile1, profile2)
        
        # Create B -> A separately
        create_relation(profile2, profile1)
        
        # Both should exist
        relations = Relation.query.all()
        assert len(relations) == 2


@pytest.mark.unit
class TestFriendRequestModel:
    """Tests for FriendRequest model."""
    
    def test_create_friend_request(self, db, create_account, create_profile):
        """Test basic friend request creation."""
        account = create_account()
        sender = create_profile(account, name='Sender')
        receiver = create_profile(account, name='Receiver')
        
        friend_request = FriendRequest(
            sender_profile_id=sender.id,
            receiver_profile_id=receiver.id,
            status='pending'
        )
        db.session.add(friend_request)
        db.session.commit()
        
        assert friend_request.id is not None
        assert friend_request.sender_profile_id == sender.id
        assert friend_request.receiver_profile_id == receiver.id
        assert friend_request.status == 'pending'
    
    def test_status_transitions(self, db, create_account, create_profile):
        """Test friend request status changes."""
        account = create_account()
        sender = create_profile(account, name='Sender')
        receiver = create_profile(account, name='Receiver')
        
        friend_request = FriendRequest(
            sender_profile_id=sender.id,
            receiver_profile_id=receiver.id,
            status='pending'
        )
        db.session.add(friend_request)
        db.session.commit()
        
        # Accept request
        friend_request.status = 'accepted'
        db.session.commit()
        assert friend_request.status == 'accepted'
        
        # Test rejection
        friend_request.status = 'rejected'
        db.session.commit()
        assert friend_request.status == 'rejected'


@pytest.mark.unit
class TestPostModel:
    """Tests for Post model."""
    
    def test_create_post(self, db, create_account, create_profile, create_post):
        """Test basic post creation."""
        account = create_account()
        profile = create_profile(account)
        post = create_post(profile, content='Test post')
        
        assert post.id is not None
        assert post.content == 'Test post'
        assert post.profile_id == profile.id
        assert post.likes == 0
        assert post.comments_count == 0
    
    def test_post_with_image(self, db, create_account, create_profile, create_post):
        """Test post with image URL."""
        account = create_account()
        profile = create_profile(account)
        post = create_post(profile, content='Post with image', image_url='http://example.com/image.jpg')
        
        assert post.image_url == 'http://example.com/image.jpg'
    
    def test_quoted_post_reference(self, db, create_account, create_profile, create_post):
        """Test quote post self-reference."""
        account = create_account()
        profile = create_profile(account)
        original_post = create_post(profile, content='Original post')
        quoted_post = create_post(profile, content='Quoting this', quoted_post_id=original_post.id)
        
        assert quoted_post.quoted_post_id == original_post.id
        assert quoted_post.quoted_post == original_post
    
    def test_like_count_tracking(self, db, create_account, create_profile, create_post):
        """Test like count field."""
        account = create_account()
        profile = create_profile(account)
        post = create_post(profile, content='Test post')
        
        post.likes = 5
        db.session.commit()
        
        assert post.likes == 5


@pytest.mark.unit
class TestMeetingModel:
    """Tests for Meeting model."""
    
    def test_create_meeting(self, db, create_account, create_profile):
        """Test basic meeting creation."""
        account = create_account()
        creator = create_profile(account, name='Creator')
        
        meeting = Meeting(
            webex_id='webex123',
            title='Test Meeting',
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            web_link='https://meet.webex.com/test',
            password='pass123',
            creator_id=creator.id
        )
        db.session.add(meeting)
        db.session.commit()
        
        assert meeting.id is not None
        assert meeting.title == 'Test Meeting'
        assert meeting.creator_id == creator.id
    
    def test_meeting_creator_relationship(self, db, create_account, create_profile):
        """Test creator relationship."""
        account = create_account()
        creator = create_profile(account, name='Creator')
        
        meeting = Meeting(
            webex_id='webex123',
            title='Test Meeting',
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            creator_id=creator.id
        )
        db.session.add(meeting)
        db.session.commit()
        
        assert meeting.creator == creator


@pytest.mark.unit
class TestMeetingInvitationModel:
    """Tests for MeetingInvitation model."""
    
    def test_create_invitation(self, db, create_account, create_profile):
        """Test basic invitation creation."""
        account = create_account()
        sender = create_profile(account, name='Sender')
        receiver = create_profile(account, name='Receiver')
        
        invitation = MeetingInvitation(
            sender_profile_id=sender.id,
            receiver_profile_id=receiver.id,
            title='Meeting Invitation',
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            status='pending'
        )
        db.session.add(invitation)
        db.session.commit()
        
        assert invitation.id is not None
        assert invitation.status == 'pending'
    
    def test_invitation_status_workflow(self, db, create_account, create_profile):
        """Test status transitions (pending→accepted→meeting created)."""
        account = create_account()
        sender = create_profile(account, name='Sender')
        receiver = create_profile(account, name='Receiver')
        
        invitation = MeetingInvitation(
            sender_profile_id=sender.id,
            receiver_profile_id=receiver.id,
            title='Test',
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            status='pending'
        )
        db.session.add(invitation)
        db.session.commit()
        
        # Accept
        invitation.status = 'accepted'
        db.session.commit()
        assert invitation.status == 'accepted'
        
        # Decline
        invitation.status = 'declined'
        db.session.commit()
        assert invitation.status == 'declined'


@pytest.mark.unit
class TestNotificationModel:
    """Tests for Notification model."""
    
    def test_create_notification(self, db, create_account, create_notification):
        """Test basic notification creation."""
        account = create_account()
        notification = create_notification(account, title='Test', message='Test message')
        
        assert notification.id is not None
        assert notification.title == 'Test'
        assert notification.message == 'Test message'
        assert notification.read is False
    
    def test_notification_read_status(self, db, create_account, create_notification):
        """Test read status toggle."""
        account = create_account()
        notification = create_notification(account)
        
        assert notification.read is False
        
        notification.read = True
        db.session.commit()
        
        assert notification.read is True
    
    def test_notification_type_field(self, db, create_account, create_notification):
        """Test notification type field."""
        account = create_account()
        notification = create_notification(account, notification_type='warning')
        
        assert notification.type == 'warning'
    
    def test_related_id_tracking(self, db, create_account, create_notification):
        """Test related_id for linking to other entities."""
        account = create_account()
        notification = create_notification(account, related_id='123')
        
        assert notification.related_id == '123'
