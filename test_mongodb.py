from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables from th`e .env file
load_dotenv()
# Directly use the connection string (just for testing)
mongo_uri = "Your_key"

try:
    # Connect to MongoDB
    print("Attempting to connect to MongoDB...")
    client = MongoClient(mongo_uri)
    
    # Test the connection
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")

    # Create/access the database
    db = client.chatbot
    messages = db.messages

    # Test insertion
    test_message = {
        "channel_id": "test",
        "user_id": "test",
        "message": "Test message",
        "timestamp": "123456789"
    }

    print("Attempting to insert test message...")
    result = messages.insert_one(test_message)
    print("Inserted document ID:", result.inserted_id)

    print("Attempting to retrieve test message...")
    found_message = messages.find_one({"channel_id": "test"})
    print("Found message:", found_message)

except Exception as e:
    print(f"An error occurred: {str(e)}")