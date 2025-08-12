# AI-Powered Customer Support Chatbot

An intelligent customer support chatbot integrated with Salesforce CRM that provides automated first-level support across multiple channels (web, WhatsApp, Slack).

## Overview

This chatbot automates customer support by:
- Detecting customer intent using fine-tuned BERT models
- Fetching real-time customer data from Salesforce CRM
- Providing dynamic responses across multiple channels
- Caching frequent queries with Redis for optimal performance
- Automatically escalating complex queries to human agents

## Technical Architecture

- **Backend**: Python + FastAPI for REST endpoints
- **NLP Engine**: Hugging Face Transformers for intent classification
- **Database**: MongoDB for chat history storage
- **Cache Layer**: Redis for frequent queries and user context
- **CRM Integration**: Salesforce REST API for live customer data
- **Testing**: PyTest for functional tests

## Key Features

- Intent detection with fine-tuned BERT model
- Dynamic responses using Salesforce customer data
- Multi-channel integration (Slack, WhatsApp, website widget)
- Automated fallback to live agents for unrecognized queries
- Real-time response caching with Redis

## Performance Metrics

- **Response Time**: Reduced from ~6s to 3.6s (40% improvement)
- **Automation Rate**: 60% of customer queries resolved automatically
- **Multi-channel Support**: Integrated with 3 communication channels

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configurations
   ```

3. **Start Services**:
   ```bash
   # Start MongoDB and Redis
   docker-compose up -d
   
   # Run the application
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Access the API**:
   - API Documentation: http://localhost:8000/docs
   - Chat Interface: http://localhost:8000/chat

## API Endpoints

- `POST /chat` - Send message to chatbot
- `GET /chat/history/{user_id}` - Get chat history
- `POST /webhooks/slack` - Slack integration
- `POST /webhooks/whatsapp` - WhatsApp integration
- `GET /health` - Health check

## Project Structure

```
app/
├── main.py                 # FastAPI application entry point
├── core/
│   ├── config.py          # Configuration settings
│   ├── database.py        # MongoDB connection
│   └── cache.py           # Redis cache management
├── models/
│   └── schemas.py         # Pydantic models
├── services/
│   ├── nlp_service.py     # NLP intent detection
│   ├── salesforce_service.py  # Salesforce integration
│   ├── chatbot_service.py # Core chatbot logic
│   ├── slack_service.py   # Slack integration
│   └── whatsapp_service.py # WhatsApp integration
├── api/
│   └── routes/
│       ├── chat.py        # Chat endpoints
│       └── webhooks.py    # Webhook endpoints
└── tests/                 # Test suite
```

## Development

Run tests:
```bash
pytest tests/ -v
```

Format code:
```bash
black app/
```

## Extensions

- Voice-based query handling using Whisper ASR
- Sentiment analysis for automatic escalations
- Advanced analytics dashboard
- Multi-language support