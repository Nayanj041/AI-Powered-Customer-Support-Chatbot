// MongoDB initialization script
db = db.getSiblingDB('customer_support_chatbot');

// Create collections
db.createCollection('chat_history');
db.createCollection('user_context');
db.createCollection('intent_logs');

// Create indexes for optimal performance
db.chat_history.createIndex({ "user_id": 1, "timestamp": -1 });
db.chat_history.createIndex({ "session_id": 1 });
db.chat_history.createIndex({ "timestamp": -1 });
db.chat_history.createIndex({ "intent": 1 });

db.user_context.createIndex({ "user_id": 1 }, { unique: true });
db.user_context.createIndex({ "updated_at": 1 });

db.intent_logs.createIndex({ "intent": 1 });
db.intent_logs.createIndex({ "confidence": -1 });
db.intent_logs.createIndex({ "timestamp": -1 });

// Insert sample data for testing (optional)
db.user_context.insertOne({
    user_id: "demo_user",
    customer_id: "demo_customer_001",
    conversation_state: {},
    preferences: {
        channel: "web",
        language: "en"
    },
    last_interaction: new Date(),
    updated_at: new Date()
});

print('Database initialized successfully!');
