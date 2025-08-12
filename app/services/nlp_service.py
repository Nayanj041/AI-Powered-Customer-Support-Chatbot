from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import torch
import numpy as np
from typing import Dict, List, Tuple
from ..models.schemas import IntentPrediction, IntentType
from ..core.config import settings
import logging
import hashlib

logger = logging.getLogger(__name__)


class NLPService:
    def __init__(self):
        self.tokenizer = None
        self.model = None
        self.classifier = None
        self.intent_mapping = {
            0: IntentType.ORDER_INQUIRY,
            1: IntentType.ACCOUNT_INFO,
            2: IntentType.PRODUCT_INFO,
            3: IntentType.BILLING,
            4: IntentType.TECHNICAL_SUPPORT,
            5: IntentType.GENERAL,
            6: IntentType.ESCALATE
        }
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize the NLP models"""
        try:
            logger.info(f"Loading NLP model: {settings.huggingface_model}")
            
            # Load pre-trained BERT model for intent classification
            self.tokenizer = AutoTokenizer.from_pretrained(
                settings.huggingface_model,
                cache_dir=settings.model_cache_dir
            )
            
            # For demonstration, we'll use a sentiment classifier
            # In production, you'd use a fine-tuned model for customer support intents
            self.classifier = pipeline(
                "text-classification",
                model=settings.huggingface_model,
                tokenizer=self.tokenizer,
                device=0 if torch.cuda.is_available() else -1,
                model_kwargs={"cache_dir": settings.model_cache_dir}
            )
            
            self.is_initialized = True
            logger.info("NLP service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize NLP service: {e}")
            raise
    
    async def predict_intent(self, message: str) -> IntentPrediction:
        """Predict intent from user message"""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Preprocess message
            message = self._preprocess_message(message)
            
            # For demonstration purposes, we'll use keyword-based intent detection
            # In production, use your fine-tuned model
            intent, confidence = self._classify_intent_keywords(message)
            
            # Get alternative predictions
            alternatives = self._get_alternative_intents(message)
            
            # Extract entities (simplified)
            entities = self._extract_entities(message)
            
            return IntentPrediction(
                intent=intent,
                confidence=confidence,
                entities=entities,
                alternative_intents=alternatives
            )
            
        except Exception as e:
            logger.error(f"Error predicting intent: {e}")
            return IntentPrediction(
                intent=IntentType.GENERAL,
                confidence=0.5,
                entities={},
                alternative_intents=[]
            )
    
    def _preprocess_message(self, message: str) -> str:
        """Preprocess the input message"""
        # Convert to lowercase and strip
        message = message.lower().strip()
        
        # Remove extra whitespaces
        import re
        message = re.sub(r'\s+', ' ', message)
        
        return message
    
    def _classify_intent_keywords(self, message: str) -> Tuple[IntentType, float]:
        """Classify intent using keyword matching (simplified approach)"""
        
        # Define keyword patterns for different intents
        intent_keywords = {
            IntentType.ORDER_INQUIRY: [
                'order', 'delivery', 'shipping', 'track', 'status', 'when will',
                'where is my', 'shipped', 'delivered', 'package'
            ],
            IntentType.ACCOUNT_INFO: [
                'account', 'profile', 'login', 'password', 'username', 'email',
                'update', 'change', 'personal information'
            ],
            IntentType.PRODUCT_INFO: [
                'product', 'item', 'specification', 'feature', 'price', 'cost',
                'available', 'in stock', 'details', 'description'
            ],
            IntentType.BILLING: [
                'bill', 'payment', 'charge', 'invoice', 'refund', 'money',
                'credit card', 'subscription', 'plan', 'cost'
            ],
            IntentType.TECHNICAL_SUPPORT: [
                'not working', 'error', 'bug', 'issue', 'problem', 'broken',
                'help', 'support', 'technical', 'fix', 'troubleshoot'
            ],
            IntentType.ESCALATE: [
                'manager', 'supervisor', 'human', 'agent', 'speak to', 'talk to',
                'escalate', 'complaint', 'unsatisfied', 'disappointed'
            ]
        }
        
        # Calculate scores for each intent
        scores = {}
        for intent, keywords in intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in message)
            if score > 0:
                scores[intent] = score / len(keywords)
        
        if scores:
            best_intent = max(scores, key=scores.get)
            confidence = min(scores[best_intent] * 2, 1.0)  # Scale confidence
            return best_intent, confidence
        
        return IntentType.GENERAL, 0.6
    
    def _get_alternative_intents(self, message: str) -> List[Dict[str, float]]:
        """Get alternative intent predictions"""
        # Simplified implementation
        alternatives = []
        
        # This would typically come from your model's prediction probabilities
        intent_keywords = {
            'order': IntentType.ORDER_INQUIRY,
            'account': IntentType.ACCOUNT_INFO,
            'product': IntentType.PRODUCT_INFO,
            'payment': IntentType.BILLING,
            'technical': IntentType.TECHNICAL_SUPPORT
        }
        
        for keyword, intent in intent_keywords.items():
            if keyword in message:
                alternatives.append({
                    "intent": intent.value,
                    "confidence": 0.3 + np.random.random() * 0.4
                })
        
        return alternatives[:3]  # Return top 3 alternatives
    
    def _extract_entities(self, message: str) -> Dict[str, any]:
        """Extract entities from the message (simplified)"""
        entities = {}
        
        # Extract order numbers (pattern: order #12345 or order number 12345)
        import re
        order_pattern = r'(?:order\s*#?|order\s+number\s*)(\d+)'
        order_match = re.search(order_pattern, message, re.IGNORECASE)
        if order_match:
            entities['order_number'] = order_match.group(1)
        
        # Extract email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, message)
        if email_match:
            entities['email'] = email_match.group(0)
        
        # Extract phone numbers (simplified)
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        phone_match = re.search(phone_pattern, message)
        if phone_match:
            entities['phone'] = phone_match.group(0)
        
        # Extract product names (this would be more sophisticated in production)
        product_keywords = ['iphone', 'laptop', 'tablet', 'headphones', 'watch']
        for keyword in product_keywords:
            if keyword in message.lower():
                entities['product'] = keyword
                break
        
        return entities
    
    def generate_message_hash(self, message: str) -> str:
        """Generate hash for message caching"""
        normalized_message = self._preprocess_message(message)
        return hashlib.md5(normalized_message.encode()).hexdigest()
    
    async def is_escalation_needed(self, message: str, confidence: float) -> bool:
        """Determine if the query should be escalated to a human agent"""
        
        # Escalate if confidence is below threshold
        if confidence < settings.confidence_threshold:
            return True
        
        # Escalate for specific keywords
        escalation_keywords = [
            'angry', 'frustrated', 'complaint', 'manager', 'supervisor',
            'legal', 'lawsuit', 'terrible', 'awful', 'worst'
        ]
        
        message_lower = message.lower()
        if any(keyword in message_lower for keyword in escalation_keywords):
            return True
        
        return False


# Global NLP service instance
nlp_service = NLPService()
