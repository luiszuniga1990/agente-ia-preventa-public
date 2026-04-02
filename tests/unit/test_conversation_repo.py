"""Tests unitarios para el repositorio de conversaciones."""

from src.services.conversation_repo import (
    add_message,
    create_conversation,
    get_conversation,
    list_conversations,
    update_status,
)


class TestCreateConversation:
    """Tests para crear conversaciones."""

    def test_create_conversation_returns_conversation_object(self, dynamodb_resource):
        conv = create_conversation(dynamodb_resource, "user-1", "es")
        assert conv.user_id == "user-1"
        assert conv.language == "es"
        assert conv.status == "active"
        assert conv.messages == []
        assert conv.conversation_id

    def test_create_conversation_persists_in_dynamodb(self, dynamodb_resource):
        conv = create_conversation(dynamodb_resource, "user-1", "en")
        retrieved = get_conversation(dynamodb_resource, conv.conversation_id)
        assert retrieved is not None
        assert retrieved.conversation_id == conv.conversation_id
        assert retrieved.user_id == "user-1"
        assert retrieved.language == "en"


class TestGetConversation:
    """Tests para obtener conversaciones."""

    def test_get_existing_conversation(self, dynamodb_resource):
        conv = create_conversation(dynamodb_resource, "user-1", "pt")
        result = get_conversation(dynamodb_resource, conv.conversation_id)
        assert result is not None
        assert result.conversation_id == conv.conversation_id
        assert result.language == "pt"

    def test_get_nonexistent_conversation_returns_none(self, dynamodb_resource):
        result = get_conversation(dynamodb_resource, "nonexistent-id")
        assert result is None


class TestAddMessage:
    """Tests para agregar mensajes."""

    def test_add_single_message(self, dynamodb_resource):
        conv = create_conversation(dynamodb_resource, "user-1", "es")
        add_message(dynamodb_resource, conv.conversation_id, "user-1", "user", "Hola")
        updated = get_conversation(dynamodb_resource, conv.conversation_id)
        assert len(updated.messages) == 1
        assert updated.messages[0]["role"] == "user"
        assert updated.messages[0]["content"] == "Hola"
        assert "timestamp" in updated.messages[0]

    def test_add_multiple_messages_preserves_order(self, dynamodb_resource):
        conv = create_conversation(dynamodb_resource, "user-1", "es")
        add_message(dynamodb_resource, conv.conversation_id, "user-1", "user", "Msg 1")
        add_message(dynamodb_resource, conv.conversation_id, "user-1", "assistant", "Msg 2")
        add_message(dynamodb_resource, conv.conversation_id, "user-1", "user", "Msg 3")
        updated = get_conversation(dynamodb_resource, conv.conversation_id)
        assert len(updated.messages) == 3
        assert updated.messages[0]["content"] == "Msg 1"
        assert updated.messages[1]["content"] == "Msg 2"
        assert updated.messages[2]["content"] == "Msg 3"

    def test_add_message_updates_updated_at(self, dynamodb_resource):
        conv = create_conversation(dynamodb_resource, "user-1", "es")
        original_updated = conv.updated_at
        add_message(dynamodb_resource, conv.conversation_id, "user-1", "user", "Test")
        updated = get_conversation(dynamodb_resource, conv.conversation_id)
        assert updated.updated_at >= original_updated


class TestListConversations:
    """Tests para listar conversaciones."""

    def test_list_conversations_for_user(self, dynamodb_resource):
        create_conversation(dynamodb_resource, "user-1", "es")
        create_conversation(dynamodb_resource, "user-1", "en")
        create_conversation(dynamodb_resource, "user-2", "pt")
        result = list_conversations(dynamodb_resource, "user-1")
        assert len(result) == 2
        assert all(c.user_id == "user-1" for c in result)

    def test_list_conversations_empty_for_unknown_user(self, dynamodb_resource):
        result = list_conversations(dynamodb_resource, "unknown-user")
        assert result == []

    def test_list_conversations_ordered_by_date_descending(self, dynamodb_resource):
        c1 = create_conversation(dynamodb_resource, "user-1", "es")
        c2 = create_conversation(dynamodb_resource, "user-1", "en")
        result = list_conversations(dynamodb_resource, "user-1")
        assert len(result) == 2
        assert result[0].created_at >= result[1].created_at


class TestUpdateStatus:
    """Tests para actualizar estado."""

    def test_update_status_to_completed(self, dynamodb_resource):
        conv = create_conversation(dynamodb_resource, "user-1", "es")
        assert conv.status == "active"
        update_status(dynamodb_resource, conv.conversation_id, "user-1", "completed")
        updated = get_conversation(dynamodb_resource, conv.conversation_id)
        assert updated.status == "completed"

    def test_update_status_updates_updated_at(self, dynamodb_resource):
        conv = create_conversation(dynamodb_resource, "user-1", "es")
        original = conv.updated_at
        update_status(dynamodb_resource, conv.conversation_id, "user-1", "completed")
        updated = get_conversation(dynamodb_resource, conv.conversation_id)
        assert updated.updated_at >= original
