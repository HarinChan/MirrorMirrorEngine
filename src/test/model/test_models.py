"""
Unit tests for database models.
Tests model creation, relationships, constraints, and business logic.
"""

import pytest
from datetime import datetime
from werkzeug.security import check_password_hash
from sqlalchemy.exc import IntegrityError

from src.app.model.profile import Profile
from src.app.model.relation import Relation
from src.app.model.friendrequest import FriendRequest
from src.app.model.post import Post
from src.app.model.meeting import Meeting
from src.app.model.meetinginvitation import MeetingInvitation
from src.app.model.notification import Notification
from src.app.model.conversation import Conversation
from src.app.model.message import Message, MessageRead, MessageReaction


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
        
        friend_request = FriendRequest()
        friend_request.sender_profile_id = sender.id
        friend_request.receiver_profile_id = receiver.id
        friend_request.status = 'pending'

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
        
        friend_request = FriendRequest()
        friend_request.sender_profile_id = sender.id
        friend_request.receiver_profile_id = receiver.id
        friend_request.status = 'pending'

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
        
        meeting = Meeting()
        meeting.webex_id = 'webex123'
        meeting.title = 'Test Meeting'
        meeting.start_time = datetime.utcnow()
        meeting.end_time = datetime.utcnow()
        meeting.web_link = 'https://meet.webex.com/test'
        meeting.password = 'pass123'
        meeting.creator_id = creator.id
        
        db.session.add(meeting)
        db.session.commit()
        
        assert meeting.id is not None
        assert meeting.title == 'Test Meeting'
        assert meeting.creator_id == creator.id
    
    def test_meeting_creator_relationship(self, db, create_account, create_profile):
        """Test creator relationship."""
        account = create_account()
        creator = create_profile(account, name='Creator')
        
        meeting = Meeting()
        meeting.webex_id = 'webex123'
        meeting.title = 'Test Meeting'
        meeting.start_time = datetime.utcnow()
        meeting.end_time = datetime.utcnow()
        meeting.creator_id = creator.id

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
        
        invitation = MeetingInvitation()
        invitation.sender_profile_id = sender.id
        invitation.receiver_profile_id = receiver.id
        invitation.title = 'Meeting Invitation'
        invitation.start_time = datetime.utcnow()
        invitation.end_time = datetime.utcnow()
        invitation.status = 'pending'

        db.session.add(invitation)
        db.session.commit()
        
        assert invitation.id is not None
        assert invitation.status == 'pending'
    
    def test_invitation_status_workflow(self, db, create_account, create_profile):
        """Test status transitions (pending→accepted→meeting created)."""
        account = create_account()
        sender = create_profile(account, name='Sender')
        receiver = create_profile(account, name='Receiver')
        
        invitation = MeetingInvitation()
        invitation.sender_profile_id = sender.id
        invitation.receiver_profile_id = receiver.id
        invitation.title = 'Meeting Invitation'
        invitation.start_time = datetime.utcnow()
        invitation.end_time = datetime.utcnow()
        invitation.status = 'pending'
        
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


@pytest.mark.unit
class TestConversationModel:
    """Tests for Conversation model."""
    
    def test_create_direct_conversation(self, db, create_profile, create_account, create_conversation):
        """Test basic direct message conversation creation."""
        account1 = create_account(email='user1@example.com')
        account2 = create_account(email='user2@example.com')
        profile1 = create_profile(account1, name='Profile 1')
        profile2 = create_profile(account2, name='Profile 2')
        
        conversation = create_conversation(
            participants=[profile1, profile2],
            conversation_type='direct'
        )
        
        assert conversation.id is not None
        assert conversation.type == 'direct'
        assert profile1 in conversation.participants
        assert profile2 in conversation.participants
        assert len(conversation.participants) == 2
    
    def test_create_group_conversation(self, db, create_profile, create_account, create_conversation):
        """Test group conversation creation with title."""
        account = create_account()
        profile1 = create_profile(account, name='Profile 1')
        profile2 = create_profile(account, name='Profile 2')
        profile3 = create_profile(account, name='Profile 3')
        
        conversation = create_conversation(
            participants=[profile1, profile2, profile3],
            conversation_type='group',
            title='Study Group'
        )
        
        assert conversation.type == 'group'
        assert conversation.title == 'Study Group'
        assert len(conversation.participants) == 3
    
    def test_conversation_timestamps(self, db, create_profile, create_account, create_conversation):
        """Test that created_at and updated_at are automatically set."""
        account = create_account()
        profile = create_profile(account)
        
        conversation = create_conversation(participants=[profile])
        
        assert conversation.created_at is not None
        assert conversation.updated_at is not None
        assert isinstance(conversation.created_at, datetime)
        assert isinstance(conversation.updated_at, datetime)
    
    def test_conversation_without_title_for_direct(self, db, create_profile, create_account):
        """Test direct conversation without title field."""
        account1 = create_account(email='user1@example.com')
        account2 = create_account(email='user2@example.com')
        profile1 = create_profile(account1)
        profile2 = create_profile(account2)
        
        conversation = Conversation()
        conversation.type = 'direct'
        conversation.participants = [profile1, profile2]
        
        db.session.add(conversation)
        db.session.commit()
        
        assert conversation.title is None
        assert conversation.type == 'direct'
    
    def test_conversation_participants_relationship(self, db, create_profile, create_account):
        """Test participants many-to-many relationship."""
        account = create_account()
        profile1 = create_profile(account, name='Profile 1')
        profile2 = create_profile(account, name='Profile 2')
        profile3 = create_profile(account, name='Profile 3')
        
        conversation = Conversation()
        conversation.type = 'group'
        conversation.title = 'Team Chat'
        conversation.participants = [profile1, profile2, profile3]
        
        db.session.add(conversation)
        db.session.commit()
        
        # Verify all participants are stored
        retrieved = db.session.get(Conversation, conversation.id)
        assert len(retrieved.participants) == 3
        assert profile1 in retrieved.participants
        assert profile2 in retrieved.participants
        assert profile3 in retrieved.participants
    
    def test_conversation_repr(self, db, create_profile, create_account):
        """Test __repr__ method."""
        account = create_account()
        profile = create_profile(account)
        
        conversation = Conversation()
        conversation.type = 'direct'
        conversation.participants = [profile]
        
        db.session.add(conversation)
        db.session.commit()
        
        repr_str = repr(conversation)
        assert 'Conversation' in repr_str
        assert 'direct' in repr_str


@pytest.mark.unit
class TestMessageModel:
    """Tests for Message model."""
    
    def test_create_text_message(self, db, create_profile, create_account, create_conversation, create_message):
        """Test basic text message creation."""
        account = create_account()
        profile = create_profile(account)
        conversation = create_conversation(participants=[profile])
        
        message = create_message(
            conversation=conversation,
            sender=profile,
            content='Hello world',
            message_type='text'
        )
        
        assert message.id is not None
        assert message.content == 'Hello world'
        assert message.conversation_id == conversation.id
        assert message.sender_profile_id == profile.id
        assert message.message_type == 'text'
        assert message.deleted is False
    
    def test_create_image_message(self, db, create_profile, create_account, create_conversation, create_message):
        """Test image message with attachment URL."""
        account = create_account()
        profile = create_profile(account)
        conversation = create_conversation(participants=[profile])
        
        message = create_message(
            conversation=conversation,
            sender=profile,
            content='Check this out',
            message_type='image',
            attachment_url='https://example.com/image.jpg'
        )
        
        assert message.message_type == 'image'
        assert message.attachment_url == 'https://example.com/image.jpg'
    
    def test_create_file_message(self, db, create_profile, create_account, create_conversation, create_message):
        """Test file message type."""
        account = create_account()
        profile = create_profile(account)
        conversation = create_conversation(participants=[profile])
        
        message = create_message(
            conversation=conversation,
            sender=profile,
            content='Shared file',
            message_type='file',
            attachment_url='https://example.com/document.pdf'
        )
        
        assert message.message_type == 'file'
    
    def test_create_system_message(self, db, create_profile, create_account, create_conversation):
        """Test system message type."""
        account = create_account()
        profile = create_profile(account)
        conversation = create_conversation(participants=[profile])
        
        message = Message()
        message.conversation_id = conversation.id
        message.sender_profile_id = profile.id
        message.content = 'User joined the conversation'
        message.message_type = 'system'
        
        db.session.add(message)
        db.session.commit()
        
        assert message.message_type == 'system'
    
    def test_message_timestamps(self, db, create_profile, create_account, create_conversation, create_message):
        """Test message creation timestamp."""
        account = create_account()
        profile = create_profile(account)
        conversation = create_conversation(participants=[profile])
        
        message = create_message(conversation=conversation, sender=profile)
        
        assert message.created_at is not None
        assert isinstance(message.created_at, datetime)
        assert message.edited_at is None
    
    def test_message_edit_tracking(self, db, create_profile, create_account, create_conversation, create_message):
        """Test edited_at timestamp when message is edited."""
        account = create_account()
        profile = create_profile(account)
        conversation = create_conversation(participants=[profile])
        
        message = create_message(conversation=conversation, sender=profile, content='Original')
        assert message.edited_at is None
        
        # Simulate editing
        message.content = 'Edited content'
        message.edited_at = datetime.utcnow()
        db.session.commit()
        
        assert message.edited_at is not None
    
    def test_message_soft_delete(self, db, create_profile, create_account, create_conversation, create_message):
        """Test soft delete with deleted flag."""
        account = create_account()
        profile = create_profile(account)
        conversation = create_conversation(participants=[profile])
        
        message = create_message(conversation=conversation, sender=profile)
        assert message.deleted is False
        
        # Soft delete
        message.deleted = True
        db.session.commit()
        
        assert message.deleted is True
    
    def test_message_sender_relationship(self, db, create_profile, create_account, create_conversation, create_message):
        """Test sender profile relationship."""
        account = create_account()
        profile = create_profile(account)
        conversation = create_conversation(participants=[profile])
        
        message = create_message(conversation=conversation, sender=profile)
        
        assert message.sender == profile
        assert message.sender_profile_id == profile.id
    
    def test_message_conversation_relationship(self, db, create_profile, create_account, create_conversation, create_message):
        """Test message-conversation relationship with cascade delete."""
        account = create_account()
        profile = create_profile(account)
        conversation = create_conversation(participants=[profile])
        
        message = create_message(conversation=conversation, sender=profile)
        message_id = message.id
        conversation_id = conversation.id
        
        # Delete conversation
        db.session.delete(conversation)
        db.session.commit()
        
        # Message should be deleted due to cascade
        assert db.session.get(Message, message_id) is None
    
    def test_message_repr(self, db, create_profile, create_account, create_conversation, create_message):
        """Test __repr__ method."""
        account = create_account()
        profile = create_profile(account)
        conversation = create_conversation(participants=[profile])
        
        message = create_message(conversation=conversation, sender=profile)
        
        repr_str = repr(message)
        assert 'Message' in repr_str
        assert 'Conversation' in repr_str


@pytest.mark.unit
class TestMessageReadModel:
    """Tests for MessageRead model."""
    
    def test_create_message_read(self, db, create_profile, create_account, create_conversation, create_message, create_message_read):
        """Test message read tracking."""
        account1 = create_account(email='user1@example.com')
        account2 = create_account(email='user2@example.com')
        profile1 = create_profile(account1)
        profile2 = create_profile(account2)
        
        conversation = Conversation()
        conversation.type = 'direct'
        conversation.participants = [profile1, profile2]
        db.session.add(conversation)
        db.session.commit()
        
        message = Message()
        message.conversation_id = conversation.id
        message.sender_profile_id = profile1.id
        message.content = 'Test message'
        db.session.add(message)
        db.session.commit()
        
        # Mark as read by second participant
        message_read = MessageRead()
        message_read.message_id = message.id
        message_read.profile_id = profile2.id
        db.session.add(message_read)
        db.session.commit()
        
        assert message_read.id is not None
        assert message_read.message_id == message.id
        assert message_read.profile_id == profile2.id
    
    def test_message_read_timestamp(self, db, create_profile, create_account, create_conversation, create_message):
        """Test read_at timestamp."""
        account1 = create_account(email='user1@example.com')
        account2 = create_account(email='user2@example.com')
        profile1 = create_profile(account1)
        profile2 = create_profile(account2)
        
        conversation = Conversation()
        conversation.type = 'direct'
        conversation.participants = [profile1, profile2]
        db.session.add(conversation)
        db.session.commit()
        
        message = Message()
        message.conversation_id = conversation.id
        message.sender_profile_id = profile1.id
        message.content = 'Test'
        db.session.add(message)
        db.session.commit()
        
        message_read = MessageRead()
        message_read.message_id = message.id
        message_read.profile_id = profile2.id
        db.session.add(message_read)
        db.session.commit()
        
        assert message_read.read_at is not None
        assert isinstance(message_read.read_at, datetime)
    
    def test_unique_constraint(self, db, create_profile, create_account, create_conversation, create_message):
        """Test unique constraint on (message_id, profile_id)."""
        account1 = create_account(email='user1@example.com')
        account2 = create_account(email='user2@example.com')
        profile1 = create_profile(account1)
        profile2 = create_profile(account2)
        
        conversation = Conversation()
        conversation.type = 'direct'
        conversation.participants = [profile1, profile2]
        db.session.add(conversation)
        db.session.commit()
        
        message = Message()
        message.conversation_id = conversation.id
        message.sender_profile_id = profile1.id
        message.content = 'Test'
        db.session.add(message)
        db.session.commit()
        
        # Create first read entry
        read1 = MessageRead()
        read1.message_id = message.id
        read1.profile_id = profile2.id
        db.session.add(read1)
        db.session.commit()
        
        # Attempting to create duplicate should fail
        with pytest.raises(IntegrityError):
            read2 = MessageRead()
            read2.message_id = message.id
            read2.profile_id = profile2.id
            db.session.add(read2)
            db.session.commit()
    
    def test_message_read_repr(self, db, create_profile, create_account, create_conversation, create_message):
        """Test __repr__ method."""
        account1 = create_account(email='user1@example.com')
        account2 = create_account(email='user2@example.com')
        profile1 = create_profile(account1)
        profile2 = create_profile(account2)
        
        conversation = Conversation()
        conversation.type = 'direct'
        conversation.participants = [profile1, profile2]
        db.session.add(conversation)
        db.session.commit()
        
        message = Message()
        message.conversation_id = conversation.id
        message.sender_profile_id = profile1.id
        message.content = 'Test'
        db.session.add(message)
        db.session.commit()
        
        message_read = MessageRead()
        message_read.message_id = message.id
        message_read.profile_id = profile2.id
        db.session.add(message_read)
        db.session.commit()
        
        repr_str = repr(message_read)
        assert 'MessageRead' in repr_str


@pytest.mark.unit
class TestMessageReactionModel:
    """Tests for MessageReaction model."""
    
    def test_create_message_reaction(self, db, create_profile, create_account, create_conversation, create_message):
        """Test basic emoji reaction creation."""
        account1 = create_account(email='user1@example.com')
        account2 = create_account(email='user2@example.com')
        profile1 = create_profile(account1)
        profile2 = create_profile(account2)
        
        conversation = Conversation()
        conversation.type = 'direct'
        conversation.participants = [profile1, profile2]
        db.session.add(conversation)
        db.session.commit()
        
        message = Message()
        message.conversation_id = conversation.id
        message.sender_profile_id = profile1.id
        message.content = 'Great idea!'
        db.session.add(message)
        db.session.commit()
        
        # React with emoji
        reaction = MessageReaction()
        reaction.message_id = message.id
        reaction.profile_id = profile2.id
        reaction.emoji = '👍'
        db.session.add(reaction)
        db.session.commit()
        
        assert reaction.id is not None
        assert reaction.emoji == '👍'
        assert reaction.message_id == message.id
        assert reaction.profile_id == profile2.id
    
    def test_multiple_emoji_reactions(self, db, create_profile, create_account, create_conversation, create_message):
        """Test different emoji reactions to same message."""
        account1 = create_account(email='user1@example.com')
        account2 = create_account(email='user2@example.com')
        profile1 = create_profile(account1)
        profile2 = create_profile(account2)
        
        conversation = Conversation()
        conversation.type = 'direct'
        conversation.participants = [profile1, profile2]
        db.session.add(conversation)
        db.session.commit()
        
        message = Message()
        message.conversation_id = conversation.id
        message.sender_profile_id = profile1.id
        message.content = 'Test'
        db.session.add(message)
        db.session.commit()
        
        # Add different reactions
        emojis = ['👍', '❤️', '😂', '🎉']
        for emoji in emojis:
            reaction = MessageReaction()
            reaction.message_id = message.id
            reaction.profile_id = profile2.id
            reaction.emoji = emoji
            db.session.add(reaction)
        db.session.commit()
        
        # All reactions should be stored
        reactions = db.session.query(MessageReaction).filter_by(
            message_id=message.id,
            profile_id=profile2.id
        ).all()
        assert len(reactions) == 4
    
    def test_reaction_timestamp(self, db, create_profile, create_account, create_conversation, create_message):
        """Test reaction creation timestamp."""
        account1 = create_account(email='user1@example.com')
        account2 = create_account(email='user2@example.com')
        profile1 = create_profile(account1)
        profile2 = create_profile(account2)
        
        conversation = Conversation()
        conversation.type = 'direct'
        conversation.participants = [profile1, profile2]
        db.session.add(conversation)
        db.session.commit()
        
        message = Message()
        message.conversation_id = conversation.id
        message.sender_profile_id = profile1.id
        message.content = 'Test'
        db.session.add(message)
        db.session.commit()
        
        reaction = MessageReaction()
        reaction.message_id = message.id
        reaction.profile_id = profile2.id
        reaction.emoji = '👍'
        db.session.add(reaction)
        db.session.commit()
        
        assert reaction.created_at is not None
        assert isinstance(reaction.created_at, datetime)
    
    def test_unique_constraint(self, db, create_profile, create_account, create_conversation, create_message):
        """Test unique constraint on (message_id, profile_id, emoji)."""
        account1 = create_account(email='user1@example.com')
        account2 = create_account(email='user2@example.com')
        profile1 = create_profile(account1)
        profile2 = create_profile(account2)
        
        conversation = Conversation()
        conversation.type = 'direct'
        conversation.participants = [profile1, profile2]
        db.session.add(conversation)
        db.session.commit()
        
        message = Message()
        message.conversation_id = conversation.id
        message.sender_profile_id = profile1.id
        message.content = 'Test'
        db.session.add(message)
        db.session.commit()
        
        # Create first reaction
        reaction1 = MessageReaction()
        reaction1.message_id = message.id
        reaction1.profile_id = profile2.id
        reaction1.emoji = '👍'
        db.session.add(reaction1)
        db.session.commit()
        
        # Attempting to create duplicate should fail
        with pytest.raises(IntegrityError):
            reaction2 = MessageReaction()
            reaction2.message_id = message.id
            reaction2.profile_id = profile2.id
            reaction2.emoji = '👍'
            db.session.add(reaction2)
            db.session.commit()
    
    def test_allow_same_emoji_by_different_profiles(self, db, create_profile, create_account, create_conversation, create_message):
        """Test that same emoji can be used by different profiles."""
        account1 = create_account(email='user1@example.com')
        account2 = create_account(email='user2@example.com')
        account3 = create_account(email='user3@example.com')
        profile1 = create_profile(account1)
        profile2 = create_profile(account2)
        profile3 = create_profile(account3)
        
        conversation = Conversation()
        conversation.type = 'group'
        conversation.participants = [profile1, profile2, profile3]
        db.session.add(conversation)
        db.session.commit()
        
        message = Message()
        message.conversation_id = conversation.id
        message.sender_profile_id = profile1.id
        message.content = 'Love this!'
        db.session.add(message)
        db.session.commit()
        
        # Both profile2 and profile3 react with same emoji
        reaction1 = MessageReaction()
        reaction1.message_id = message.id
        reaction1.profile_id = profile2.id
        reaction1.emoji = '❤️'
        db.session.add(reaction1)
        
        reaction2 = MessageReaction()
        reaction2.message_id = message.id
        reaction2.profile_id = profile3.id
        reaction2.emoji = '❤️'
        db.session.add(reaction2)
        db.session.commit()
        
        # Both should exist
        reactions = db.session.query(MessageReaction).filter_by(
            message_id=message.id,
            emoji='❤️'
        ).all()
        assert len(reactions) == 2
    
    def test_reaction_repr(self, db, create_profile, create_account, create_conversation, create_message):
        """Test __repr__ method."""
        account1 = create_account(email='user1@example.com')
        account2 = create_account(email='user2@example.com')
        profile1 = create_profile(account1)
        profile2 = create_profile(account2)
        
        conversation = Conversation()
        conversation.type = 'direct'
        conversation.participants = [profile1, profile2]
        db.session.add(conversation)
        db.session.commit()
        
        message = Message()
        message.conversation_id = conversation.id
        message.sender_profile_id = profile1.id
        message.content = 'Test'
        db.session.add(message)
        db.session.commit()
        
        reaction = MessageReaction()
        reaction.message_id = message.id
        reaction.profile_id = profile2.id
        reaction.emoji = '👍'
        db.session.add(reaction)
        db.session.commit()
        
        repr_str = repr(reaction)
        assert 'MessageReaction' in repr_str
        assert '👍' in repr_str


@pytest.mark.unit
class TestRecentCallModel:
    assert True