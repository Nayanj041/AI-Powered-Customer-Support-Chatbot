import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test root endpoint"""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert data["name"] == "AI-Powered Customer Support Chatbot"
    assert "endpoints" in data


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Test health check endpoint"""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "services" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_chat_endpoint_basic(client: AsyncClient, sample_chat_message):
    """Test basic chat endpoint functionality"""
    response = await client.post("/api/chat", json=sample_chat_message)
    assert response.status_code == 200
    data = response.json()
    
    assert "response" in data
    assert "intent" in data
    assert "confidence" in data
    assert "requires_escalation" in data
    assert "session_id" in data
    assert "response_time_ms" in data
    assert isinstance(data["response"], str)
    assert len(data["response"]) > 0


@pytest.mark.asyncio
async def test_chat_endpoint_order_inquiry(client: AsyncClient, sample_order_inquiry):
    """Test chat endpoint with order inquiry"""
    response = await client.post("/api/chat", json=sample_order_inquiry)
    assert response.status_code == 200
    data = response.json()
    
    assert "response" in data
    assert data["intent"] == "order_inquiry"
    assert "order" in data["response"].lower()


@pytest.mark.asyncio
async def test_chat_endpoint_account_inquiry(client: AsyncClient, sample_account_inquiry):
    """Test chat endpoint with account inquiry"""
    response = await client.post("/api/chat", json=sample_account_inquiry)
    assert response.status_code == 200
    data = response.json()
    
    assert "response" in data
    assert data["intent"] == "account_info"
    assert any(keyword in data["response"].lower() for keyword in ["account", "email", "information"])


@pytest.mark.asyncio
async def test_chat_endpoint_escalation(client: AsyncClient, sample_escalation_message):
    """Test chat endpoint with escalation trigger"""
    response = await client.post("/api/chat", json=sample_escalation_message)
    assert response.status_code == 200
    data = response.json()
    
    assert "response" in data
    assert data["requires_escalation"] is True


@pytest.mark.asyncio
async def test_chat_history_empty_user(client: AsyncClient):
    """Test chat history for user with no history"""
    response = await client.get("/api/chat/history/nonexistent_user")
    assert response.status_code == 200
    data = response.json()
    
    assert "user_id" in data
    assert "history" in data
    assert "count" in data
    assert data["count"] == 0
    assert len(data["history"]) == 0


@pytest.mark.asyncio
async def test_chat_history_after_conversation(client: AsyncClient, sample_chat_message):
    """Test chat history after having a conversation"""
    # Send a message first
    chat_response = await client.post("/api/chat", json=sample_chat_message)
    assert chat_response.status_code == 200
    
    # Then get history
    user_id = sample_chat_message["user_id"]
    response = await client.get(f"/api/chat/history/{user_id}")
    assert response.status_code == 200
    data = response.json()
    
    assert data["user_id"] == user_id
    assert data["count"] > 0
    assert len(data["history"]) > 0


@pytest.mark.asyncio
async def test_chat_endpoint_invalid_request(client: AsyncClient):
    """Test chat endpoint with invalid request"""
    # Missing required fields
    invalid_message = {
        "message": "Hello"
        # Missing user_id
    }
    
    response = await client.post("/api/chat", json=invalid_message)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_chat_endpoint_empty_message(client: AsyncClient):
    """Test chat endpoint with empty message"""
    empty_message = {
        "message": "",
        "user_id": "test_user",
        "channel": "web"
    }
    
    response = await client.post("/api/chat", json=empty_message)
    assert response.status_code == 422  # Should fail validation


@pytest.mark.asyncio
async def test_nonexistent_endpoint(client: AsyncClient):
    """Test accessing nonexistent endpoint"""
    response = await client.get("/api/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_webhook_slack_without_signature(client: AsyncClient):
    """Test Slack webhook without proper authentication"""
    slack_data = {
        "type": "url_verification",
        "challenge": "test_challenge"
    }
    
    response = await client.post("/api/webhooks/slack", json=slack_data)
    assert response.status_code == 200
    data = response.json()
    assert data["challenge"] == "test_challenge"


@pytest.mark.asyncio
async def test_webhook_whatsapp(client: AsyncClient):
    """Test WhatsApp webhook"""
    whatsapp_data = {
        "From": "whatsapp:+1234567890",
        "To": "whatsapp:+0987654321",
        "Body": "Hello, I need help",
        "MessageSid": "test_message_sid",
        "AccountSid": "test_account_sid"
    }
    
    response = await client.post("/api/webhooks/whatsapp", data=whatsapp_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_chat_web_interface(client: AsyncClient):
    """Test web chat interface"""
    response = await client.get("/chat")
    assert response.status_code == 200
    content = response.text
    assert "Customer Support Chatbot" in content
    assert "chat-container" in content


@pytest.mark.asyncio
async def test_session_persistence(client: AsyncClient):
    """Test that session IDs are maintained across requests"""
    message1 = {
        "message": "Hello",
        "user_id": "session_test_user",
        "channel": "web"
    }
    
    # Send first message
    response1 = await client.post("/api/chat", json=message1)
    assert response1.status_code == 200
    data1 = response1.json()
    session_id = data1["session_id"]
    
    # Send second message with same session
    message2 = {
        "message": "How are you?",
        "user_id": "session_test_user",
        "session_id": session_id,
        "channel": "web"
    }
    
    response2 = await client.post("/api/chat", json=message2)
    assert response2.status_code == 200
    data2 = response2.json()
    
    assert data2["session_id"] == session_id
