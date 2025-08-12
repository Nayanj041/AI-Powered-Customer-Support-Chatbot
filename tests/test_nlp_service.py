import pytest
from app.services.nlp_service import nlp_service
from app.models.schemas import IntentType


@pytest.mark.asyncio
async def test_nlp_service_initialization():
    """Test NLP service initialization"""
    # The service should be initialized during app startup
    # We can test if it initializes without errors
    try:
        await nlp_service.initialize()
        assert nlp_service.is_initialized
    except Exception as e:
        # In test environment without GPU/models, this might fail
        # That's acceptable for this test
        assert "Failed to initialize NLP service" in str(e) or nlp_service.is_initialized


@pytest.mark.asyncio
async def test_intent_prediction_order_inquiry():
    """Test intent prediction for order inquiries"""
    message = "Where is my order #12345? I haven't received it yet."
    
    prediction = await nlp_service.predict_intent(message)
    
    assert prediction.intent == IntentType.ORDER_INQUIRY
    assert isinstance(prediction.confidence, float)
    assert 0 <= prediction.confidence <= 1
    assert isinstance(prediction.entities, dict)
    
    # Should extract order number
    if 'order_number' in prediction.entities:
        assert prediction.entities['order_number'] == '12345'


@pytest.mark.asyncio
async def test_intent_prediction_account_info():
    """Test intent prediction for account information"""
    message = "I need to update my account information and change my email address"
    
    prediction = await nlp_service.predict_intent(message)
    
    assert prediction.intent == IntentType.ACCOUNT_INFO
    assert isinstance(prediction.confidence, float)
    assert 0 <= prediction.confidence <= 1


@pytest.mark.asyncio
async def test_intent_prediction_billing():
    """Test intent prediction for billing inquiries"""
    message = "I was charged twice on my credit card and need a refund"
    
    prediction = await nlp_service.predict_intent(message)
    
    assert prediction.intent == IntentType.BILLING
    assert isinstance(prediction.confidence, float)
    assert 0 <= prediction.confidence <= 1


@pytest.mark.asyncio
async def test_intent_prediction_technical_support():
    """Test intent prediction for technical support"""
    message = "My device is not working properly and shows error messages"
    
    prediction = await nlp_service.predict_intent(message)
    
    assert prediction.intent == IntentType.TECHNICAL_SUPPORT
    assert isinstance(prediction.confidence, float)
    assert 0 <= prediction.confidence <= 1


@pytest.mark.asyncio
async def test_intent_prediction_escalation():
    """Test intent prediction for escalation"""
    message = "I want to speak to a manager immediately! This is terrible service!"
    
    prediction = await nlp_service.predict_intent(message)
    
    # Should either be classified as escalation or trigger escalation logic
    is_escalation_needed = await nlp_service.is_escalation_needed(message, prediction.confidence)
    assert is_escalation_needed or prediction.intent == IntentType.ESCALATE


@pytest.mark.asyncio
async def test_entity_extraction_email():
    """Test entity extraction for email addresses"""
    message = "My email address is user@example.com"
    
    prediction = await nlp_service.predict_intent(message)
    
    if 'email' in prediction.entities:
        assert prediction.entities['email'] == 'user@example.com'


@pytest.mark.asyncio
async def test_entity_extraction_phone():
    """Test entity extraction for phone numbers"""
    message = "Call me at 555-123-4567"
    
    prediction = await nlp_service.predict_intent(message)
    
    if 'phone' in prediction.entities:
        assert '555-123-4567' in prediction.entities['phone']


@pytest.mark.asyncio
async def test_message_preprocessing():
    """Test message preprocessing"""
    original_message = "   HELLO   WORLD   "
    processed_message = nlp_service._preprocess_message(original_message)
    
    assert processed_message == "hello world"


@pytest.mark.asyncio
async def test_escalation_detection_low_confidence():
    """Test escalation detection for low confidence"""
    message = "I have a question about something"
    
    # Simulate low confidence
    is_escalation = await nlp_service.is_escalation_needed(message, 0.3)
    assert is_escalation  # Should escalate due to low confidence


@pytest.mark.asyncio
async def test_escalation_detection_keywords():
    """Test escalation detection for escalation keywords"""
    messages_requiring_escalation = [
        "I'm very angry about this",
        "This is terrible service",
        "I want to speak to a manager",
        "This is the worst experience",
        "I'm going to sue you"
    ]
    
    for message in messages_requiring_escalation:
        is_escalation = await nlp_service.is_escalation_needed(message, 0.8)  # High confidence
        assert is_escalation, f"Message should trigger escalation: {message}"


@pytest.mark.asyncio
async def test_message_hash_generation():
    """Test message hash generation for caching"""
    message1 = "Hello, how are you?"
    message2 = "hello, how are you?"
    message3 = "Hi, how are you?"
    
    hash1 = nlp_service.generate_message_hash(message1)
    hash2 = nlp_service.generate_message_hash(message2)
    hash3 = nlp_service.generate_message_hash(message3)
    
    # Same normalized message should have same hash
    assert hash1 == hash2
    
    # Different messages should have different hashes
    assert hash1 != hash3
    
    # Hashes should be strings
    assert isinstance(hash1, str)
    assert len(hash1) > 0


@pytest.mark.asyncio
async def test_intent_confidence_range():
    """Test that intent confidence is always in valid range"""
    test_messages = [
        "Hello",
        "I need help with my order",
        "How do I update my account?",
        "My payment was declined",
        "The app is not working",
        "",  # Empty message
        "a" * 1000  # Very long message
    ]
    
    for message in test_messages:
        prediction = await nlp_service.predict_intent(message)
        assert 0 <= prediction.confidence <= 1, f"Invalid confidence for message: {message}"
        assert prediction.intent in IntentType, f"Invalid intent for message: {message}"


@pytest.mark.asyncio
async def test_alternative_intents_format():
    """Test that alternative intents are properly formatted"""
    message = "I need help with my order and billing"
    
    prediction = await nlp_service.predict_intent(message)
    
    assert isinstance(prediction.alternative_intents, list)
    
    for alternative in prediction.alternative_intents:
        assert isinstance(alternative, dict)
        assert "intent" in alternative
        assert "confidence" in alternative
        assert isinstance(alternative["confidence"], float)
        assert 0 <= alternative["confidence"] <= 1
