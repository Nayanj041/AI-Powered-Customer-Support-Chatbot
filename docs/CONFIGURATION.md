# Configuration Guide

## Environment Variables

The application uses environment variables for configuration. Copy `.env.example` to `.env` and configure the following:

### API Configuration

```bash
# FastAPI Configuration
API_HOST=0.0.0.0           # API host address
API_PORT=8000              # API port number
DEBUG=True                 # Debug mode (use False in production)
SECRET_KEY=your-secret-key-here  # Secret key for security
```

### Database Configuration

```bash
# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017  # MongoDB connection URL
MONGODB_DATABASE=customer_support_chatbot  # Database name
```

### Cache Configuration

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379  # Redis connection URL
REDIS_DB=0                         # Redis database number
CACHE_TTL=3600                     # Cache TTL in seconds (1 hour)
```

### Salesforce Integration

```bash
# Salesforce Configuration
SALESFORCE_USERNAME=your-salesforce-username
SALESFORCE_PASSWORD=your-salesforce-password
SALESFORCE_SECURITY_TOKEN=your-security-token
SALESFORCE_DOMAIN=login  # Use 'test' for sandbox
```

**Getting Salesforce Credentials:**
1. Log into Salesforce
2. Go to Settings → Personal Information → Reset Security Token
3. Check your email for the security token
4. For sandbox environments, use `SALESFORCE_DOMAIN=test`

### Slack Integration

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_SIGNING_SECRET=your-slack-signing-secret
```

**Setting up Slack Bot:**
1. Go to https://api.slack.com/apps
2. Create a new app
3. Add bot token scopes: `chat:write`, `channels:history`, `groups:history`, `im:history`, `mpim:history`
4. Install app to workspace
5. Copy Bot User OAuth Token and Signing Secret

### WhatsApp/Twilio Integration

```bash
# WhatsApp/Twilio Configuration
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=+1234567890
```

**Setting up Twilio WhatsApp:**
1. Create Twilio account
2. Get WhatsApp sandbox or approved WhatsApp Business number
3. Configure webhook URL: `https://your-domain.com/api/webhooks/whatsapp`
4. Copy Account SID and Auth Token

### NLP Configuration

```bash
# NLP Model Configuration
HUGGINGFACE_MODEL=bert-base-uncased  # Hugging Face model name
MODEL_CACHE_DIR=./models/cache       # Local model cache directory
CONFIDENCE_THRESHOLD=0.7             # Minimum confidence for responses
```

### Logging Configuration

```bash
# Logging Configuration
LOG_LEVEL=INFO      # Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_FORMAT=json     # Log format (json, text)
```

## Database Setup

### MongoDB

#### Local Installation
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y mongodb

# macOS with Homebrew
brew tap mongodb/brew
brew install mongodb-community

# Start MongoDB
sudo systemctl start mongodb  # Linux
brew services start mongodb-community  # macOS
```

#### Using Docker
```bash
docker run -d --name mongodb -p 27017:27017 mongo:7
```

#### Configuration
The application automatically creates necessary collections and indexes. No manual setup required.

### Redis

#### Local Installation
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install redis-server

# macOS with Homebrew
brew install redis

# Start Redis
sudo systemctl start redis-server  # Linux
brew services start redis          # macOS
```

#### Using Docker
```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

## Model Configuration

### Hugging Face Models

The application uses BERT-based models for intent classification. Default model is `bert-base-uncased`.

#### Custom Models
To use a custom model:
1. Upload your model to Hugging Face Hub
2. Set `HUGGINGFACE_MODEL` to your model name
3. Ensure model is compatible with `AutoTokenizer` and `AutoModelForSequenceClassification`

#### Local Models
To use local models:
1. Place model files in `models/cache/model-name/`
2. Set `HUGGINGFACE_MODEL` to the path
3. Update `MODEL_CACHE_DIR` if needed

## Security Configuration

### Production Security Checklist

1. **Environment Variables**
   - Use strong, unique SECRET_KEY
   - Never commit .env files to version control
   - Use environment-specific configurations

2. **Database Security**
   - Enable MongoDB authentication
   - Use SSL/TLS for database connections
   - Restrict network access

3. **API Security**
   - Implement rate limiting
   - Use HTTPS in production
   - Add authentication/authorization
   - Validate all inputs

4. **Webhook Security**
   - Verify webhook signatures
   - Use HTTPS endpoints
   - Implement proper error handling

### SSL/TLS Configuration

For production, use SSL/TLS certificates:

```bash
# Using Let's Encrypt with Certbot
sudo apt-get install certbot
sudo certbot certonly --standalone -d yourdomain.com

# Update your reverse proxy (nginx/apache) configuration
```

## Performance Configuration

### Caching Strategy

```bash
# Cache TTL settings
CACHE_TTL=3600              # General cache TTL (1 hour)
USER_CONTEXT_TTL=1800       # User context TTL (30 minutes)
SALESFORCE_DATA_TTL=600     # Salesforce data TTL (10 minutes)
FREQUENT_QUERY_TTL=7200     # Frequent queries TTL (2 hours)
```

### Database Optimization

1. **Indexes**: Automatically created by the application
2. **Connection Pooling**: Configure MongoDB connection pool size
3. **Query Optimization**: Use projection to limit returned fields

### Application Performance

```bash
# Uvicorn configuration for production
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker
```

## Development vs Production

### Development Configuration

```bash
DEBUG=True
LOG_LEVEL=DEBUG
MONGODB_URL=mongodb://localhost:27017
REDIS_URL=redis://localhost:6379
```

### Production Configuration

```bash
DEBUG=False
LOG_LEVEL=INFO
MONGODB_URL=mongodb://prod-mongodb:27017/customer_support?authSource=admin&ssl=true
REDIS_URL=rediss://prod-redis:6380/0
SECRET_KEY=strong-production-secret-key
```

## Monitoring Configuration

### Health Checks

The application provides health check endpoints for monitoring:
- `/api/health` - Overall health status
- Service-specific health checks included

### Logging

Configure structured logging for production:

```python
# Example logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        }
    },
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'chatbot.log',
            'formatter': 'json'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['file']
    }
}
```

## Troubleshooting

### Common Issues

1. **MongoDB Connection Failed**
   - Check MongoDB is running
   - Verify connection URL
   - Check network connectivity

2. **Redis Connection Failed**
   - Ensure Redis is running
   - Verify Redis URL and port
   - Check Redis configuration

3. **Model Loading Issues**
   - Check internet connectivity for model download
   - Verify model name and cache directory
   - Ensure sufficient disk space

4. **Webhook Issues**
   - Verify webhook URLs are accessible
   - Check SSL certificates
   - Validate webhook signatures

### Debug Mode

Enable debug mode for troubleshooting:

```bash
DEBUG=True
LOG_LEVEL=DEBUG
```

This enables detailed logging and error messages.
