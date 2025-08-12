from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True
    secret_key: str = "default-secret-key-change-in-production"
    
    # MongoDB Configuration
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "customer_support_chatbot"
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0
    cache_ttl: int = 3600  # Cache TTL in seconds
    
    # Salesforce Configuration
    salesforce_username: Optional[str] = None
    salesforce_password: Optional[str] = None
    salesforce_security_token: Optional[str] = None
    salesforce_domain: str = "login"  # or 'test' for sandbox
    
    # Slack Configuration
    slack_bot_token: Optional[str] = None
    slack_signing_secret: Optional[str] = None
    
    # WhatsApp/Twilio Configuration
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    
    # NLP Model Configuration
    huggingface_model: str = "bert-base-uncased"
    model_cache_dir: str = "./models/cache"
    confidence_threshold: float = 0.7
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Create model cache directory if it doesn't exist
os.makedirs(settings.model_cache_dir, exist_ok=True)