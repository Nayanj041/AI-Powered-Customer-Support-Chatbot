# API Documentation

## Base URL
```
http://localhost:8000
```

## Authentication
Currently, the API does not require authentication. In production, implement proper authentication and authorization.

## Endpoints

### Chat Endpoints

#### Send Message
```http
POST /api/chat
```

Send a message to the chatbot and receive a response.

**Request Body:**
```json
{
  "message": "I need help with my order",
  "user_id": "unique_user_id",
  "session_id": "optional_session_id",
  "channel": "web",
  "metadata": {
    "source": "mobile_app",
    "version": "1.0.0"
  }
}
```

**Response:**
```json
{
  "response": "I can help you with your order. Could you please provide your order number?",
  "intent": "order_inquiry",
  "confidence": 0.95,
  "requires_escalation": false,
  "session_id": "session_123",
  "response_time_ms": 245
}
```

#### Get Chat History
```http
GET /api/chat/history/{user_id}?session_id={session_id}&limit={limit}
```

Retrieve chat history for a user.

**Parameters:**
- `user_id` (path): User identifier
- `session_id` (query, optional): Specific session ID
- `limit` (query, optional): Maximum number of messages (default: 50, max: 100)

**Response:**
```json
{
  "user_id": "user_123",
  "session_id": "session_456",
  "history": [
    {
      "id": "msg_001",
      "user_id": "user_123",
      "session_id": "session_456",
      "message": "Hello",
      "response": "Hi! How can I help you today?",
      "message_type": "user",
      "intent": "general",
      "confidence": 0.8,
      "channel": "web",
      "timestamp": "2025-08-12T10:30:00Z"
    }
  ],
  "count": 1
}
```

### Webhook Endpoints

#### Slack Webhook
```http
POST /api/webhooks/slack
```

Handle Slack webhook events.

**Headers:**
- `X-Slack-Signature`: Slack signature for verification
- `X-Slack-Request-Timestamp`: Request timestamp

**Request Body:** Slack event payload

#### WhatsApp Webhook
```http
POST /api/webhooks/whatsapp
```

Handle WhatsApp webhook events via Twilio.

**Request Body:** Form data from Twilio webhook

### Health Check

#### Health Status
```http
GET /api/health
```

Check the health status of the application and its services.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-12T10:30:00Z",
  "services": {
    "mongodb": "healthy",
    "redis": "healthy",
    "nlp": "ready",
    "salesforce": "connected"
  },
  "version": "1.0.0"
}
```

### Web Interface

#### Chat Interface
```http
GET /chat
```

Access the web-based chat interface for testing and customer use.

#### Root Information
```http
GET /
```

Get basic information about the API and available endpoints.

## Error Responses

All endpoints return appropriate HTTP status codes and error messages:

### 400 Bad Request
```json
{
  "error": "Bad Request",
  "message": "Invalid request data",
  "timestamp": "2025-08-12T10:30:00Z"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "user_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal Server Error",
  "message": "An unexpected error occurred",
  "timestamp": "2025-08-12T10:30:00Z"
}
```

## Rate Limits

- **Chat API**: 100 requests per minute per user
- **Webhooks**: 1000 requests per minute per channel
- **Health Check**: No limit

## Intent Types

The NLP service can classify messages into the following intents:

- `order_inquiry`: Questions about orders, shipping, delivery
- `account_info`: Account information, profile updates
- `product_info`: Product details, specifications, availability
- `billing`: Billing questions, payments, refunds
- `technical_support`: Technical issues, troubleshooting
- `general`: General questions, greetings
- `escalate`: Requests for human agent

## Channel Types

Supported communication channels:

- `web`: Web chat interface
- `slack`: Slack integration
- `whatsapp`: WhatsApp integration via Twilio

## Best Practices

1. **User IDs**: Use consistent, unique user identifiers across sessions
2. **Session Management**: Maintain session IDs for conversation context
3. **Error Handling**: Always handle potential errors gracefully
4. **Rate Limiting**: Respect rate limits to ensure service availability
5. **Metadata**: Include relevant metadata for analytics and debugging

## Examples

### Basic Chat Flow
```python
import requests

# Send initial message
response = requests.post('http://localhost:8000/api/chat', json={
    'message': 'Hello, I need help',
    'user_id': 'user_123',
    'channel': 'web'
})

chat_response = response.json()
session_id = chat_response['session_id']

# Continue conversation
response = requests.post('http://localhost:8000/api/chat', json={
    'message': 'I want to track my order #12345',
    'user_id': 'user_123',
    'session_id': session_id,
    'channel': 'web'
})
```

### Get Chat History
```python
response = requests.get('http://localhost:8000/api/chat/history/user_123')
history = response.json()
```

### Health Check
```python
response = requests.get('http://localhost:8000/api/health')
health_status = response.json()
```
