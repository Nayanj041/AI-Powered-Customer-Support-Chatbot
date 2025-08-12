import pytest
from unittest.mock import AsyncMock, Mock, patch
from app.services.chatbot_service import chatbot_service
from app.models.schemas import ChatMessage, Channel, IntentType


@pytest.mark.asyncio
async def test_process_message_basic():
    """Test basic message processing"""
    message = ChatMessage(
        message="Hello, I need help",
        user_id="test_user",
        channel=Channel.WEB
    )
    
    response = await chatbot_service.process_message(message)
    
    assert response.response is not None
    assert isinstance(response.response, str)
    assert len(response.response) > 0
    assert response.session_id is not None
    assert isinstance(response.requires_escalation, bool)
    assert isinstance(response.response_time_ms, int)
    assert response.response_time_ms > 0


@pytest.mark.asyncio
async def test_process_order_inquiry():
    """Test processing order inquiry"""
    message = ChatMessage(
        message="Where is my order #12345?",
        user_id="test_user_order",
        channel=Channel.WEB
    )
    
    response = await chatbot_service.process_message(message)
    
    assert response.intent == IntentType.ORDER_INQUIRY.value
    assert "order" in response.response.lower()


@pytest.mark.asyncio
async def test_process_account_inquiry():
    """Test processing account inquiry"""
    message = ChatMessage(
        message="I need to update my email address",
        user_id="test_user_account",
        channel=Channel.WEB
    )
    
    response = await chatbot_service.process_message(message)
    
    assert response.intent == IntentType.ACCOUNT_INFO.value
    assert any(keyword in response.response.lower() for keyword in ["account", "email", "information"])


@pytest.mark.asyncio
async def test_process_greeting():
    """Test processing greeting messages"""
    greetings = ["Hello", "Hi", "Good morning", "Hey there"]
    
    for greeting in greetings:
        message = ChatMessage(
            message=greeting,
            user_id=f"test_user_{greeting}",
            channel=Channel.WEB
        )
        
        response = await chatbot_service.process_message(message)
        
        assert response.response is not None
        assert len(response.response) > 0
        # Should contain helpful information
        assert any(keyword in response.response.lower() for keyword in ["help", "assist", "support"])


@pytest.mark.asyncio
async def test_process_escalation_message():
    """Test processing messages that should trigger escalation"""
    escalation_messages = [
        "I want to speak to a manager",
        "This is terrible service",
        "I'm very angry about this"
    ]
    
    for msg_text in escalation_messages:
        message = ChatMessage(
            message=msg_text,
            user_id=f"test_escalation_{hash(msg_text)}",
            channel=Channel.WEB
        )
        
        response = await chatbot_service.process_message(message)
        
        # Should either trigger escalation or have very low confidence
        assert response.requires_escalation or response.confidence < 0.5


@pytest.mark.asyncio
async def test_session_id_persistence():
    """Test that session ID is maintained when provided"""
    session_id = "test_session_123"
    
    message = ChatMessage(
        message="Hello",
        user_id="test_session_user",
        session_id=session_id,
        channel=Channel.WEB
    )
    
    response = await chatbot_service.process_message(message)
    
    assert response.session_id == session_id


@pytest.mark.asyncio
async def test_session_id_generation():
    """Test that session ID is generated when not provided"""
    message = ChatMessage(
        message="Hello",
        user_id="test_session_gen_user",
        channel=Channel.WEB
    )
    
    response = await chatbot_service.process_message(message)
    
    assert response.session_id is not None
    assert len(response.session_id) > 0
    assert response.session_id != message.user_id


@pytest.mark.asyncio
async def test_get_chat_history_empty():
    """Test getting chat history for new user"""
    history = await chatbot_service.get_chat_history("nonexistent_user")
    
    assert isinstance(history, list)
    assert len(history) == 0


@pytest.mark.asyncio
async def test_get_chat_history_with_messages():
    """Test getting chat history after conversation"""
    user_id = "test_history_user"
    
    # Send a message first
    message = ChatMessage(
        message="Test message for history",
        user_id=user_id,
        channel=Channel.WEB
    )
    
    await chatbot_service.process_message(message)
    
    # Get history
    history = await chatbot_service.get_chat_history(user_id)
    
    assert isinstance(history, list)
    assert len(history) > 0


@pytest.mark.asyncio
async def test_personalized_query_detection():
    """Test detection of personalized queries"""
    personalized_queries = [
        "my order #12345",
        "my account information",
        "my profile settings",
        "order number 67890",
        "user@example.com"
    ]
    
    non_personalized_queries = [
        "what are your hours?",
        "how do I place an order?",
        "what products do you sell?"
    ]
    
    for query in personalized_queries:
        assert chatbot_service._is_personalized_query(query), f"Should detect as personalized: {query}"
    
    for query in non_personalized_queries:
        assert not chatbot_service._is_personalized_query(query), f"Should not detect as personalized: {query}"


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in message processing"""
    # Test with extreme cases
    extreme_messages = [
        ChatMessage(message="", user_id="test_empty", channel=Channel.WEB),
        ChatMessage(message="a" * 10000, user_id="test_long", channel=Channel.WEB),  # Very long message
    ]
    
    for message in extreme_messages:
        try:
            response = await chatbot_service.process_message(message)
            # Should still return a valid response
            assert response.response is not None
            assert response.session_id is not None
        except Exception as e:
            # If it fails, it should fail gracefully
            assert "error" in str(e).lower() or "invalid" in str(e).lower()


@pytest.mark.asyncio
async def test_different_channels():
    """Test processing messages from different channels"""
    channels = [Channel.WEB, Channel.SLACK, Channel.WHATSAPP]
    
    for channel in channels:
        message = ChatMessage(
            message="Hello from " + channel.value,
            user_id=f"test_user_{channel.value}",
            channel=channel
        )
        
        response = await chatbot_service.process_message(message)
        
        assert response.response is not None
        assert response.session_id is not None


@pytest.mark.asyncio
async def test_metadata_handling():
    """Test handling of message metadata"""
    metadata = {
        "source": "mobile_app",
        "version": "1.2.3",
        "platform": "ios"
    }
    
    message = ChatMessage(
        message="Test with metadata",
        user_id="test_metadata_user",
        channel=Channel.WEB,
        metadata=metadata
    )
    
    response = await chatbot_service.process_message(message)
    
    # Should process successfully despite metadata
    assert response.response is not None
    assert response.session_id is not None


@pytest.mark.asyncio
async def test_response_templates_loading():
    """Test that response templates are loaded correctly"""
    templates = chatbot_service.response_templates
    
    assert isinstance(templates, dict)
    assert len(templates) > 0
    
    # Should have templates for main intent types
    expected_intents = [
        IntentType.ORDER_INQUIRY.value,
        IntentType.ACCOUNT_INFO.value,
        IntentType.PRODUCT_INFO.value,
        IntentType.BILLING.value,
        IntentType.TECHNICAL_SUPPORT.value
    ]
    
    for intent in expected_intents:
        assert intent in templates
        assert isinstance(templates[intent], list)
        assert len(templates[intent]) > 0


@pytest.mark.asyncio
async def test_escalation_responses():
    """Test that escalation responses are appropriate"""
    escalation_responses = chatbot_service.escalation_phrases
    
    assert isinstance(escalation_responses, list)
    assert len(escalation_responses) > 0
    
    for response in escalation_responses:
        assert isinstance(response, str)
        assert len(response) > 0
        # Should contain escalation-related keywords
        assert any(keyword in response.lower() for keyword in ["human", "agent", "escalat", "transfer"])
