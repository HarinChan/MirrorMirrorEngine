"""
Integration tests for messaging blueprint.
Tests conversation management, message sending/editing/deletion, read receipts, and reactions.
"""

import pytest
import json

from src.app.blueprint import messaging_bp as messaging_module
from src.app.model.conversation import Conversation
from src.app.model.message import Message, MessageRead, MessageReaction
from src.app.model.relation import Relation


@pytest.mark.integration
class TestConversationManagement:
    """Tests for conversation endpoints."""
    
    def test_start_conversation_creates_direct_message_with_friend(
        self, client, auth_token, create_account, create_profile, db
    ):
        """Test starting a new direct message conversation with a friend."""
        token, account1 = auth_token
        profile1 = create_profile(account=account1, name="Profile 1")
        
        account2 = create_account("friend@example.com", "Password123!")
        profile2 = create_profile(account=account2, name="Profile 2")
        
        # Create friendship
        relation = Relation(
            from_profile_id=profile1.id,
            to_profile_id=profile2.id,
            status='accepted'
        )
        db.session.add(relation)
        db.session.commit()
        
        response = client.post(
            "/api/conversations/start",
            json={"friendId": profile2.id},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 201
        payload = response.get_json()
        assert payload["msg"] == "Conversation created"
        assert payload["conversation"]["type"] == "direct"
        assert payload["conversation"]["participants"][0]["id"] == profile2.id
        
        # Verify conversation in database
        conversation = Conversation.query.get(payload["conversation"]["id"])
        assert conversation is not None
        assert conversation.type == "direct"
        assert profile1 in conversation.participants
        assert profile2 in conversation.participants
    
    def test_start_conversation_with_non_friend_fails(
        self, client, auth_token, create_account, create_profile
    ):
        """Test that conversation cannot be started with non-friend."""
        token, account1 = auth_token
        profile1 = create_profile(account=account1, name="Profile 1")
        
        account2 = create_account("stranger@example.com", "Password123!")
        profile2 = create_profile(account=account2, name="Stranger")
        
        response = client.post(
            "/api/conversations/start",
            json={"friendId": profile2.id},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 403
        assert "can only message friends" in response.get_json()["msg"].lower()
    
    def test_start_conversation_returns_existing_if_already_exists(
        self, client, auth_token, create_account, create_profile, create_conversation, db
    ):
        """Test that restarting conversation with same friend returns existing one."""
        token, account1 = auth_token
        profile1 = create_profile(account=account1, name="Profile 1")
        
        account2 = create_account("friend@example.com", "Password123!")
        profile2 = create_profile(account=account2, name="Profile 2")
        
        # Create friendship
        relation = Relation(
            from_profile_id=profile1.id,
            to_profile_id=profile2.id,
            status='accepted'
        )
        db.session.add(relation)
        db.session.commit()
        
        # Create existing conversation
        existing_conv = create_conversation(
            participants=[profile1, profile2],
            conversation_type='direct'
        )
        existing_id = existing_conv.id
        
        # Try to start again
        response = client.post(
            "/api/conversations/start",
            json={"friendId": profile2.id},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["msg"] == "Conversation already exists"
        assert payload["conversation"]["id"] == existing_id
    
    def test_start_conversation_missing_friend_id(
        self, client, auth_token, create_profile
    ):
        """Test start_conversation validation when friendId is missing."""
        token, account = auth_token
        create_profile(account=account, name="Profile")
        
        response = client.post(
            "/api/conversations/start",
            json={},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 400
        # Blueprint returns either "Friend ID required" or "Request body is required"
        assert any(msg in response.get_json()["msg"] for msg in ["Friend ID required", "Request body is required"])
    
    def test_start_conversation_invalid_friend_id(
        self, client, auth_token, create_profile
    ):
        """Test start_conversation with invalid friend ID."""
        token, account = auth_token
        create_profile(account=account, name="Profile")
        
        response = client.post(
            "/api/conversations/start",
            json={"friendId": -1},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 400
        assert "Invalid friend ID" in response.get_json()["msg"]
    
    def test_get_conversations_lists_all_user_conversations(
        self, client, auth_token, create_account, create_profile, create_conversation, create_message
    ):
        """Test getting all conversations for a user."""
        token, account1 = auth_token
        profile1 = create_profile(account=account1, name="User")
        
        account2 = create_account("friend1@example.com", "Password123!")
        profile2 = create_profile(account=account2, name="Friend 1")
        
        account3 = create_account("friend2@example.com", "Password123!")
        profile3 = create_profile(account=account3, name="Friend 2")
        
        # Create conversations
        conv1 = create_conversation(participants=[profile1, profile2])
        conv2 = create_conversation(participants=[profile1, profile3])
        
        # Add messages
        create_message(conversation=conv1, sender=profile2, content="Hello")
        create_message(conversation=conv2, sender=profile3, content="Hi")
        
        response = client.get(
            "/api/conversations",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 200
        payload = response.get_json()
        assert "conversations" in payload
        assert len(payload["conversations"]) >= 2


@pytest.mark.integration
class Testmessaging:
    """Tests for message sending and retrieval."""
    
    def test_send_message_creates_message_in_conversation(
        self, client, auth_token, create_account, create_profile, create_conversation
    ):
        """Test sending a text message in a conversation."""
        token, account1 = auth_token
        profile1 = create_profile(account=account1, name="Sender")
        
        account2 = create_account("recipient@example.com", "Password123!")
        profile2 = create_profile(account=account2, name="Recipient")
        
        conversation = create_conversation(participants=[profile1, profile2])
        
        response = client.post(
            f"/api/conversations/{conversation.id}/messages",
            json={"content": "Test message"},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 201
        payload = response.get_json()
        assert payload["msg"] == "Message sent"
        assert payload["message"]["content"] == "Test message"
        assert payload["message"]["senderName"] == "Sender"
        
        # Verify message in database
        message = Message.query.get(payload["message"]["id"])
        assert message is not None
        assert message.sender_profile_id == profile1.id
        assert message.content == "Test message"
        assert message.message_type == "text"
        assert message.deleted is False
    
    def test_send_image_message_with_attachment_url(
        self, client, auth_token, create_account, create_profile, create_conversation
    ):
        """Test sending an image message with attachment URL."""
        token, account1 = auth_token
        profile1 = create_profile(account=account1, name="Sender")
        
        account2 = create_account("recipient@example.com", "Password123!")
        profile2 = create_profile(account=account2, name="Recipient")
        
        conversation = create_conversation(participants=[profile1, profile2])
        
        response = client.post(
            f"/api/conversations/{conversation.id}/messages",
            json={
                "content": "Check this out",
                "messageType": "image",
                "attachmentUrl": "https://example.com/image.jpg"
            },
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 201
        payload = response.get_json()
        assert payload["message"]["messageType"] == "image"
        assert payload["message"]["attachmentUrl"] == "https://example.com/image.jpg"
    
    def test_send_message_without_content_fails(
        self, client, auth_token, create_account, create_profile, create_conversation
    ):
        """Test that message without content is rejected."""
        token, account1 = auth_token
        profile1 = create_profile(account=account1, name="Sender")
        
        account2 = create_account("recipient@example.com", "Password123!")
        profile2 = create_profile(account=account2, name="Recipient")
        
        conversation = create_conversation(participants=[profile1, profile2])
        
        response = client.post(
            f"/api/conversations/{conversation.id}/messages",
            json={"content": ""},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 400
        assert "content or attachment required" in response.get_json()["msg"].lower()
    
    def test_send_message_non_participant_fails(
        self, client, auth_token, create_account, create_profile, create_conversation
    ):
        """Test that non-participant cannot send message."""
        token, account1 = auth_token
        profile1 = create_profile(account=account1, name="Non-participant")
        
        account2 = create_account("user2@example.com", "Password123!")
        profile2 = create_profile(account=account2, name="User 2")
        
        account3 = create_account("user3@example.com", "Password123!")
        profile3 = create_profile(account=account3, name="User 3")
        
        conversation = create_conversation(participants=[profile2, profile3])
        
        response = client.post(
            f"/api/conversations/{conversation.id}/messages",
            json={"content": "Unauthorized message"},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 403
        assert "Unauthorized" in response.get_json()["msg"]
    
    def test_get_messages_retrieves_conversation_messages(
        self, client, auth_token, create_account, create_profile, create_conversation, create_message
    ):
        """Test retrieving messages from a conversation."""
        token, account1 = auth_token
        profile1 = create_profile(account=account1, name="User")
        
        account2 = create_account("friend@example.com", "Password123!")
        profile2 = create_profile(account=account2, name="Friend")
        
        conversation = create_conversation(participants=[profile1, profile2])
        msg1 = create_message(conversation=conversation, sender=profile1, content="Message 1")
        msg2 = create_message(conversation=conversation, sender=profile2, content="Message 2")
        
        response = client.get(
            f"/api/conversations/{conversation.id}/messages",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 200
        payload = response.get_json()
        assert "messages" in payload
        assert len(payload["messages"]) >= 2
        assert payload["pagination"]["page"] == 1
        assert payload["pagination"]["total"] >= 2
    
    def test_get_messages_with_pagination(
        self, client, auth_token, create_account, create_profile, create_conversation, create_message
    ):
        """Test message pagination."""
        token, account1 = auth_token
        profile1 = create_profile(account=account1, name="User")
        
        account2 = create_account("friend@example.com", "Password123!")
        profile2 = create_profile(account=account2, name="Friend")
        
        conversation = create_conversation(participants=[profile1, profile2])
        
        # Create 10 messages
        for i in range(10):
            create_message(conversation=conversation, sender=profile1, content=f"Message {i}")
        
        response = client.get(
            f"/api/conversations/{conversation.id}/messages?page=1&per_page=5",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 200
        payload = response.get_json()
        assert len(payload["messages"]) == 5
        assert payload["pagination"]["page"] == 1
        assert payload["pagination"]["perPage"] == 5
        assert payload["pagination"]["total"] >= 10
        assert payload["pagination"]["hasNext"] is True


@pytest.mark.integration
class TestMessageReadReceipts:
    """Tests for message read tracking."""
    
    def test_mark_message_read_creates_read_receipt(
        self, client, auth_token, create_account, create_profile, create_conversation, create_message
    ):
        """Test marking a message as read."""
        token, account1 = auth_token
        profile1 = create_profile(account=account1, name="Reader")
        
        account2 = create_account("sender@example.com", "Password123!")
        profile2 = create_profile(account=account2, name="Sender")
        
        conversation = create_conversation(participants=[profile1, profile2])
        message = create_message(conversation=conversation, sender=profile2, content="Hello")
        
        response = client.post(
            f"/api/messages/{message.id}/read",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 200
        
        # Verify read receipt created
        read_receipt = MessageRead.query.filter_by(
            message_id=message.id,
            profile_id=profile1.id
        ).first()
        assert read_receipt is not None
    
    def test_mark_own_message_as_read_fails(
        self, client, auth_token, create_profile, create_conversation, create_message
    ):
        """Test that sender cannot mark their own message as read."""
        token, account = auth_token
        profile1 = create_profile(account=account, name="User")
        
        conversation = create_conversation(participants=[profile1])
        message = create_message(conversation=conversation, sender=profile1, content="My message")
        
        response = client.post(
            f"/api/messages/{message.id}/read",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 400
        assert "Cannot mark own message as read" in response.get_json()["msg"]
    
    def test_mark_all_read_marks_all_unread_messages(
        self, client, auth_token, create_account, create_profile, create_conversation, create_message
    ):
        """Test marking all messages in conversation as read."""
        token, account1 = auth_token
        profile1 = create_profile(account=account1, name="Reader")
        
        account2 = create_account("sender@example.com", "Password123!")
        profile2 = create_profile(account=account2, name="Sender")
        
        conversation = create_conversation(participants=[profile1, profile2])
        
        # Create multiple messages from sender
        msg1 = create_message(conversation=conversation, sender=profile2, content="Message 1")
        msg2 = create_message(conversation=conversation, sender=profile2, content="Message 2")
        msg3 = create_message(conversation=conversation, sender=profile2, content="Message 3")
        
        response = client.post(
            f"/api/conversations/{conversation.id}/mark-all-read",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 200
        payload = response.get_json()
        assert "3 messages as read" in payload["msg"]
        
        # Verify all marked as read
        for msg in [msg1, msg2, msg3]:
            read = MessageRead.query.filter_by(
                message_id=msg.id,
                profile_id=profile1.id
            ).first()
            assert read is not None


@pytest.mark.integration
class TestMessageEditing:
    """Tests for message editing."""
    
    def test_edit_message_updates_content(
        self, client, auth_token, create_profile, create_conversation, create_message
    ):
        """Test editing a message by sender."""
        token, account = auth_token
        profile = create_profile(account=account, name="User")
        
        conversation = create_conversation(participants=[profile])
        message = create_message(conversation=conversation, sender=profile, content="Original content")
        
        response = client.put(
            f"/api/messages/{message.id}",
            json={"content": "Edited content"},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["message"]["content"] == "Edited content"
        assert payload["message"]["editedAt"] is not None
        
        # Verify in database
        updated = Message.query.get(message.id)
        assert updated.content == "Edited content"
        assert updated.edited_at is not None
    
    def test_edit_message_by_non_sender_fails(
        self, client, auth_token, create_account, create_profile, create_conversation, create_message
    ):
        """Test that non-sender cannot edit message."""
        token, account1 = auth_token
        profile1 = create_profile(account=account1, name="Non-sender")
        
        account2 = create_account("sender@example.com", "Password123!")
        profile2 = create_profile(account=account2, name="Sender")
        
        conversation = create_conversation(participants=[profile1, profile2])
        message = create_message(conversation=conversation, sender=profile2, content="Original")
        
        response = client.put(
            f"/api/messages/{message.id}",
            json={"content": "Hacked content"},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 403
        assert "Unauthorized" in response.get_json()["msg"]


@pytest.mark.integration
class TestMessageDeletion:
    """Tests for message deletion (soft delete)."""
    
    def test_delete_message_soft_deletes(
        self, client, auth_token, create_profile, create_conversation, create_message
    ):
        """Test soft deleting a message."""
        token, account = auth_token
        profile = create_profile(account=account, name="User")
        
        conversation = create_conversation(participants=[profile])
        message = create_message(conversation=conversation, sender=profile, content="To delete")
        assert message.deleted is False
        
        response = client.delete(
            f"/api/messages/{message.id}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 200
        
        # Verify soft delete
        deleted = Message.query.get(message.id)
        assert deleted.deleted is True
        assert "[Message deleted]" in deleted.content
    
    def test_delete_message_by_non_sender_fails(
        self, client, auth_token, create_account, create_profile, create_conversation, create_message
    ):
        """Test that non-sender cannot delete message."""
        token, account1 = auth_token
        profile1 = create_profile(account=account1, name="Non-sender")
        
        account2 = create_account("sender@example.com", "Password123!")
        profile2 = create_profile(account=account2, name="Sender")
        
        conversation = create_conversation(participants=[profile1, profile2])
        message = create_message(conversation=conversation, sender=profile2, content="Keep this")
        
        response = client.delete(
            f"/api/messages/{message.id}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 403
        assert "Unauthorized" in response.get_json()["msg"]


@pytest.mark.integration
class TestMessageReactions:
    """Tests for emoji reactions."""
    
    def test_add_reaction_creates_emoji_reaction(
        self, client, auth_token, create_account, create_profile, create_conversation, create_message
    ):
        """Test adding an emoji reaction to a message."""
        token, account1 = auth_token
        profile1 = create_profile(account=account1, name="Reactor")
        
        account2 = create_account("sender@example.com", "Password123!")
        profile2 = create_profile(account=account2, name="Sender")
        
        conversation = create_conversation(participants=[profile1, profile2])
        message = create_message(conversation=conversation, sender=profile2, content="Great idea!")
        
        response = client.post(
            f"/api/messages/{message.id}/reactions",
            json={"emoji": "👍"},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 201
        payload = response.get_json()
        assert payload["msg"] == "Reaction added"
        assert payload["action"] == "added"
        assert payload["reaction"]["emoji"] == "👍"
        
        # Verify in database
        reaction = MessageReaction.query.filter_by(
            message_id=message.id,
            profile_id=profile1.id,
            emoji="👍"
        ).first()
        assert reaction is not None
    
    def test_toggle_reaction_removes_if_already_exists(
        self, client, auth_token, create_account, create_profile, create_conversation, create_message, db
    ):
        """Test that re-adding same emoji removes it (toggle)."""
        token, account1 = auth_token
        profile1 = create_profile(account=account1, name="Reactor")
        
        account2 = create_account("sender@example.com", "Password123!")
        profile2 = create_profile(account=account2, name="Sender")
        
        conversation = create_conversation(participants=[profile1, profile2])
        message = create_message(conversation=conversation, sender=profile2, content="React here")
        
        # Add reaction
        response1 = client.post(
            f"/api/messages/{message.id}/reactions",
            json={"emoji": "❤️"},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        assert response1.status_code == 201
        assert response1.get_json()["action"] == "added"
        
        # Toggle reaction (should remove)
        response2 = client.post(
            f"/api/messages/{message.id}/reactions",
            json={"emoji": "❤️"},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        assert response2.status_code == 200
        assert response2.get_json()["action"] == "removed"
        
        # Verify removed from database
        reaction = MessageReaction.query.filter_by(
            message_id=message.id,
            profile_id=profile1.id,
            emoji="❤️"
        ).first()
        assert reaction is None
    
    def test_get_reactions_retrieves_all_reactions(
        self, client, auth_token, create_account, create_profile, create_conversation, create_message, db
    ):
        """Test retrieving all reactions for a message."""
        token, account1 = auth_token
        profile1 = create_profile(account=account1, name="User 1")
        
        account2 = create_account("user2@example.com", "Password123!")
        profile2 = create_profile(account=account2, name="User 2")
        
        account3 = create_account("user3@example.com", "Password123!")
        profile3 = create_profile(account=account3, name="User 3")
        
        conversation = create_conversation(participants=[profile1, profile2, profile3])
        message = create_message(conversation=conversation, sender=profile1, content="Great!")
        
        # Add reactions
        reaction1 = MessageReaction(message_id=message.id, profile_id=profile1.id, emoji="👍")
        reaction2 = MessageReaction(message_id=message.id, profile_id=profile2.id, emoji="👍")
        reaction3 = MessageReaction(message_id=message.id, profile_id=profile3.id, emoji="❤️")
        db.session.add_all([reaction1, reaction2, reaction3])
        db.session.commit()
        
        response = client.get(
            f"/api/messages/{message.id}/reactions",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 200
        payload = response.get_json()
        assert "reactions" in payload
        assert len(payload["reactions"]) == 2  # Two different emojis
        
        # Find thumbs up reaction
        thumbs_up = next((r for r in payload["reactions"] if r["emoji"] == "👍"), None)
        assert thumbs_up is not None
        assert thumbs_up["count"] == 2
    
    def test_react_as_non_participant_fails(
        self, client, auth_token, create_account, create_profile, create_conversation, create_message
    ):
        """Test that non-participant cannot react to message."""
        token, account1 = auth_token
        profile1 = create_profile(account=account1, name="Non-participant")
        
        account2 = create_account("user2@example.com", "Password123!")
        profile2 = create_profile(account=account2, name="User 2")
        
        account3 = create_account("user3@example.com", "Password123!")
        profile3 = create_profile(account=account3, name="User 3")
        
        conversation = create_conversation(participants=[profile2, profile3])
        message = create_message(conversation=conversation, sender=profile2, content="React here")
        
        response = client.post(
            f"/api/messages/{message.id}/reactions",
            json={"emoji": "👍"},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 403
        assert "Unauthorized" in response.get_json()["msg"]


@pytest.mark.integration
class TestErrorHandling:
    """Tests for error conditions and edge cases."""
    
    def test_get_nonexistent_conversation_returns_404(
        self, client, auth_token
    ):
        """Test accessing non-existent conversation."""
        token, _ = auth_token
        
        response = client.get(
            "/api/conversations/99999/messages",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 404
    
    def test_message_content_length_validation(
        self, client, auth_token, create_profile, create_conversation
    ):
        """Test that oversized message is rejected."""
        token, account = auth_token
        profile = create_profile(account=account, name="User")
        conversation = create_conversation(participants=[profile])
        
        # Create message longer than 10,000 characters
        long_content = "x" * 10001
        
        response = client.post(
            f"/api/conversations/{conversation.id}/messages",
            json={"content": long_content},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 400
        assert "too long" in response.get_json()["msg"].lower()
    
    def test_invalid_message_type_rejected(
        self, client, auth_token, create_profile, create_conversation
    ):
        """Test that invalid message type is rejected."""
        token, account = auth_token
        profile = create_profile(account=account, name="User")
        conversation = create_conversation(participants=[profile])
        
        response = client.post(
            f"/api/conversations/{conversation.id}/messages",
            json={"content": "Test", "messageType": "invalid_type"},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        
        assert response.status_code == 400
        assert "Invalid message type" in response.get_json()["msg"]
    
    def test_requires_authentication(self, client):
        """Test that endpoints require authentication."""
        response = client.get("/api/conversations")
        assert response.status_code == 401
        
        response = client.post("/api/conversations/start", json={"friendId": 1})
        assert response.status_code == 401


@pytest.mark.integration
class TestMessagingCoverageGaps:
    """Additional tests focused on missing messaging blueprint branches."""

    @staticmethod
    def _headers(token):
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def test_get_conversations_user_not_found(self, client, create_jwt_token):
        token = create_jwt_token("999999")
        response = client.get("/api/conversations", headers=self._headers(token))
        assert response.status_code == 404
        assert response.get_json()["msg"] == "User not found"

    def test_get_conversations_profile_not_found(self, client, create_account, create_jwt_token):
        account = create_account(email="noprofile@getconv.test")
        token = create_jwt_token(str(account.id))
        response = client.get("/api/conversations", headers=self._headers(token))
        assert response.status_code == 404
        assert response.get_json()["msg"] == "Profile not found"

    def test_get_messages_validation_and_authorization_branches(
        self, client, create_jwt_token, create_account, create_profile, create_conversation
    ):
        ghost_token = create_jwt_token("999998")
        response = client.get("/api/conversations/1/messages", headers=self._headers(ghost_token))
        assert response.status_code == 404

        account = create_account(email="noprofile@getmsg.test")
        no_profile_token = create_jwt_token(str(account.id))
        response = client.get("/api/conversations/1/messages", headers=self._headers(no_profile_token))
        assert response.status_code == 404
        assert response.get_json()["msg"] == "Profile not found"

        owner = create_account(email="owner@getmsg.test")
        outsider = create_account(email="outsider@getmsg.test")
        owner_profile = create_profile(owner, name="Owner")
        outsider_profile = create_profile(outsider, name="Outsider")
        conversation = create_conversation(participants=[owner_profile])
        outsider_token = create_jwt_token(str(outsider.id))

        response = client.get("/api/conversations/999999/messages", headers=self._headers(outsider_token))
        assert response.status_code == 404
        assert response.get_json()["msg"] == "Conversation not found"

        response = client.get(
            f"/api/conversations/{conversation.id}/messages",
            headers=self._headers(outsider_token),
        )
        assert response.status_code == 403

        response = client.get("/api/conversations/0/messages", headers=self._headers(outsider_token))
        assert response.status_code == 400

    def test_get_messages_pagination_and_reaction_grouping(
        self, client, auth_token, create_account, create_profile, create_conversation, create_message, db
    ):
        token, account = auth_token
        me = create_profile(account=account, name="Me")
        other_account = create_account("other@grouping.test", "Password123!")
        other = create_profile(account=other_account, name="Other")
        conversation = create_conversation(participants=[me, other])

        msg = create_message(conversation=conversation, sender=other, content="hello")
        db.session.add(MessageReaction(message_id=msg.id, profile_id=other.id, emoji="👍"))
        db.session.add(MessageReaction(message_id=msg.id, profile_id=me.id, emoji="👍"))
        db.session.add(MessageRead(message_id=msg.id, profile_id=me.id))
        db.session.commit()

        response = client.get(
            f"/api/conversations/{conversation.id}/messages?page=-1&per_page=500",
            headers=self._headers(token),
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["pagination"]["page"] == 1
        assert payload["pagination"]["perPage"] == 100
        assert payload["messages"][0]["isRead"] is True
        assert payload["messages"][0]["reactions"][0]["hasReacted"] is True

        response = client.get(
            f"/api/conversations/{conversation.id}/messages?page=1&per_page=0",
            headers=self._headers(token),
        )
        assert response.status_code == 200
        assert response.get_json()["pagination"]["perPage"] == 30

    def test_send_message_validation_branches(
        self, client, auth_token, create_account, create_profile, create_conversation
    ):
        token, account = auth_token
        me = create_profile(account=account, name="Me")
        other_account = create_account("other@send.test", "Password123!")
        other = create_profile(account=other_account, name="Other")
        conversation = create_conversation(participants=[me, other])

        response = client.post(
            f"/api/conversations/{conversation.id}/messages",
            json={},
            headers=self._headers(token),
        )
        assert response.status_code == 400
        assert response.get_json()["msg"] == "Request body is required"

        response = client.post(
            f"/api/conversations/{conversation.id}/messages",
            json={"content": "x", "attachmentUrl": "h" * 501},
            headers=self._headers(token),
        )
        assert response.status_code == 400
        assert "Attachment URL too long" in response.get_json()["msg"]

        response = client.post(
            "/api/conversations/0/messages",
            json={"content": "x"},
            headers=self._headers(token),
        )
        assert response.status_code == 400

    def test_send_message_user_profile_and_conversation_not_found(
        self, client, create_jwt_token, create_account, create_profile
    ):
        ghost_token = create_jwt_token("999997")
        response = client.post("/api/conversations/1/messages", json={"content": "x"}, headers=self._headers(ghost_token))
        assert response.status_code == 404

        account = create_account(email="noprofile@send.test")
        token = create_jwt_token(str(account.id))
        response = client.post("/api/conversations/1/messages", json={"content": "x"}, headers=self._headers(token))
        assert response.status_code == 404
        assert response.get_json()["msg"] == "Profile not found"

        owner = create_account(email="owner@sendnf.test")
        owner_profile = create_profile(owner, name="Owner")
        owner_token = create_jwt_token(str(owner.id))
        response = client.post("/api/conversations/999999/messages", json={"content": "x"}, headers=self._headers(owner_token))
        assert response.status_code == 404
        assert response.get_json()["msg"] == "Conversation not found"

    def test_mark_read_and_mark_all_read_remaining_branches(
        self, client, auth_token, create_account, create_profile, create_conversation, create_message, create_jwt_token
    ):
        token, account = auth_token
        me = create_profile(account=account, name="Me")
        other_account = create_account("other@read.test", "Password123!")
        other = create_profile(account=other_account, name="Other")
        conversation = create_conversation(participants=[me, other])
        message = create_message(conversation=conversation, sender=other, content="m")

        response = client.post(f"/api/messages/0/read", headers=self._headers(token))
        assert response.status_code == 400

        ghost_token = create_jwt_token("999996")
        response = client.post(f"/api/messages/{message.id}/read", headers=self._headers(ghost_token))
        assert response.status_code == 404

        no_profile_account = create_account(email="noprofile@read.test")
        no_profile_token = create_jwt_token(str(no_profile_account.id))
        response = client.post(f"/api/messages/{message.id}/read", headers=self._headers(no_profile_token))
        assert response.status_code == 404

        response = client.post("/api/messages/999999/read", headers=self._headers(token))
        assert response.status_code == 404

        outsider_account = create_account("outsider@read.test", "Password123!")
        outsider = create_profile(outsider_account, name="Outsider")
        outsider_token = create_jwt_token(str(outsider_account.id))
        response = client.post(f"/api/messages/{message.id}/read", headers=self._headers(outsider_token))
        assert response.status_code == 403

        response = client.post(f"/api/messages/{message.id}/read", headers=self._headers(token))
        assert response.status_code == 200
        response = client.post(f"/api/messages/{message.id}/read", headers=self._headers(token))
        assert response.status_code == 200
        assert response.get_json()["msg"] == "Already marked as read"

        response = client.post("/api/conversations/0/mark-all-read", headers=self._headers(token))
        assert response.status_code == 400
        response = client.post("/api/conversations/999999/mark-all-read", headers=self._headers(token))
        assert response.status_code == 404
        response = client.post(f"/api/conversations/{conversation.id}/mark-all-read", headers=self._headers(outsider_token))
        assert response.status_code == 403

    def test_start_conversation_additional_not_found_paths(self, client, create_jwt_token, create_account):
        ghost_token = create_jwt_token("999995")
        response = client.post("/api/conversations/start", json={"friendId": 1}, headers=self._headers(ghost_token))
        assert response.status_code == 404

        account = create_account(email="noprofile@start.test")
        token = create_jwt_token(str(account.id))
        response = client.post("/api/conversations/start", json={"friendId": 1}, headers=self._headers(token))
        assert response.status_code == 404

    def test_start_conversation_friend_not_found(self, client, auth_token, create_profile):
        token, account = auth_token
        create_profile(account=account, name="Me")
        response = client.post(
            "/api/conversations/start",
            json={"friendId": 999999},
            headers=self._headers(token),
        )
        assert response.status_code == 404
        assert response.get_json()["msg"] == "Friend not found"

    def test_start_conversation_friend_id_required_branch(self, client, auth_token, create_profile):
        token, account = auth_token
        create_profile(account=account, name="Me")
        response = client.post(
            "/api/conversations/start",
            json={"notFriendId": 1},
            headers=self._headers(token),
        )
        assert response.status_code == 400
        assert response.get_json()["msg"] == "Friend ID required"

    def test_edit_delete_and_reaction_validation_branches(
        self, client, auth_token, create_profile, create_conversation, create_message
    ):
        token, account = auth_token
        me = create_profile(account=account, name="Me")
        conversation = create_conversation(participants=[me])
        message = create_message(conversation=conversation, sender=me, content="hello")

        response = client.put("/api/messages/0", json={"content": "x"}, headers=self._headers(token))
        assert response.status_code == 400
        response = client.put("/api/messages/999999", json={"content": "x"}, headers=self._headers(token))
        assert response.status_code == 404

        response = client.put(f"/api/messages/{message.id}", json={}, headers=self._headers(token))
        assert response.status_code == 400
        response = client.put(f"/api/messages/{message.id}", json={"content": "   "}, headers=self._headers(token))
        assert response.status_code == 400
        response = client.put(f"/api/messages/{message.id}", json={"content": "x" * 10001}, headers=self._headers(token))
        assert response.status_code == 400

        message.deleted = True
        from src.app.model import db
        db.session.commit()
        response = client.put(f"/api/messages/{message.id}", json={"content": "x"}, headers=self._headers(token))
        assert response.status_code == 400

        response = client.delete("/api/messages/0", headers=self._headers(token))
        assert response.status_code == 400
        response = client.delete("/api/messages/999999", headers=self._headers(token))
        assert response.status_code == 404

        response = client.post(f"/api/messages/{message.id}/reactions", json={}, headers=self._headers(token))
        assert response.status_code == 400
        response = client.post(f"/api/messages/{message.id}/reactions", json={"emoji": "   "}, headers=self._headers(token))
        assert response.status_code == 400
        response = client.post(f"/api/messages/{message.id}/reactions", json={"emoji": "x" * 11}, headers=self._headers(token))
        assert response.status_code == 400

        response = client.post("/api/messages/0/reactions", json={"emoji": "👍"}, headers=self._headers(token))
        assert response.status_code == 400
        response = client.post("/api/messages/999999/reactions", json={"emoji": "👍"}, headers=self._headers(token))
        assert response.status_code == 404

        response = client.get("/api/messages/0/reactions", headers=self._headers(token))
        assert response.status_code == 400
        response = client.get("/api/messages/999999/reactions", headers=self._headers(token))
        assert response.status_code == 404

    def test_mark_all_read_user_and_profile_not_found(self, client, create_jwt_token, create_account):
        ghost_token = create_jwt_token("999994")
        response = client.post("/api/conversations/1/mark-all-read", headers=self._headers(ghost_token))
        assert response.status_code == 404
        assert response.get_json()["msg"] == "User not found"

        account = create_account(email="noprofile@markall.test")
        token = create_jwt_token(str(account.id))
        response = client.post("/api/conversations/1/mark-all-read", headers=self._headers(token))
        assert response.status_code == 404
        assert response.get_json()["msg"] == "Profile not found"

    def test_edit_delete_and_reaction_user_profile_not_found(self, client, create_jwt_token, create_account):
        ghost_token = create_jwt_token("999993")

        response = client.put("/api/messages/1", json={"content": "x"}, headers=self._headers(ghost_token))
        assert response.status_code == 404
        assert response.get_json()["msg"] == "User not found"

        response = client.delete("/api/messages/1", headers=self._headers(ghost_token))
        assert response.status_code == 404
        assert response.get_json()["msg"] == "User not found"

        response = client.post("/api/messages/1/reactions", json={"emoji": "👍"}, headers=self._headers(ghost_token))
        assert response.status_code == 404
        assert response.get_json()["msg"] == "User not found"

        response = client.get("/api/messages/1/reactions", headers=self._headers(ghost_token))
        assert response.status_code == 404
        assert response.get_json()["msg"] == "User not found"

        account = create_account(email="noprofile@mutliendpoint.test")
        token = create_jwt_token(str(account.id))

        response = client.put("/api/messages/1", json={"content": "x"}, headers=self._headers(token))
        assert response.status_code == 404
        assert response.get_json()["msg"] == "Profile not found"

        response = client.delete("/api/messages/1", headers=self._headers(token))
        assert response.status_code == 404
        assert response.get_json()["msg"] == "Profile not found"

        response = client.post("/api/messages/1/reactions", json={"emoji": "👍"}, headers=self._headers(token))
        assert response.status_code == 404
        assert response.get_json()["msg"] == "Profile not found"

        response = client.get("/api/messages/1/reactions", headers=self._headers(token))
        assert response.status_code == 404
        assert response.get_json()["msg"] == "Profile not found"

    def test_get_reactions_unauthorized_branch(
        self, client, auth_token, create_account, create_profile, create_conversation, create_message
    ):
        token, account = auth_token
        outsider = create_profile(account=account, name="Outsider")
        a2 = create_account("react-a2@test.com", "Password123!")
        a3 = create_account("react-a3@test.com", "Password123!")
        p2 = create_profile(a2, name="P2")
        p3 = create_profile(a3, name="P3")
        conv = create_conversation(participants=[p2, p3])
        msg = create_message(conversation=conv, sender=p2, content="hi")

        response = client.get(f"/api/messages/{msg.id}/reactions", headers=self._headers(token))
        assert response.status_code == 403
        assert response.get_json()["msg"] == "Unauthorized"

    @pytest.mark.parametrize(
        "method,url,json_payload",
        [
            ("get", "/api/conversations", None),
            ("get", "/api/conversations/1/messages", None),
            ("post", "/api/conversations/1/messages", {"content": "x"}),
            ("post", "/api/messages/1/read", None),
            ("post", "/api/conversations/1/mark-all-read", None),
            ("post", "/api/conversations/start", {"friendId": 1}),
            ("put", "/api/messages/1", {"content": "x"}),
            ("delete", "/api/messages/1", None),
            ("post", "/api/messages/1/reactions", {"emoji": "👍"}),
            ("get", "/api/messages/1/reactions", None),
        ],
    )
    def test_internal_server_error_handlers(
        self, client, auth_token, create_profile, monkeypatch, method, url, json_payload
    ):
        token, account = auth_token
        create_profile(account=account, name="Me")

        def boom():
            raise RuntimeError("forced")

        monkeypatch.setattr(messaging_module, "get_jwt_identity", boom)

        request_method = getattr(client, method)
        if json_payload is None:
            response = request_method(url, headers=self._headers(token))
        else:
            response = request_method(url, json=json_payload, headers=self._headers(token))

        assert response.status_code == 500
        assert response.get_json()["msg"] == "Internal server error"
