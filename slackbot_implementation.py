import os
from datetime import datetime
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.oauth.oauth_settings import OAuthSettings
from slack_bolt.oauth.store.file import FileInstallationStore
import openai
from pymongo import MongoClient
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq

# Load environment variables
load_dotenv()
oauth_settings = OAuthSettings(
    client_id=os.environ["SLACK_CLIENT_ID"],
    client_secret=os.environ["SLACK_CLIENT_SECRET"],
    scopes=["app_mentions:read", "chat:write"],
    installation_store=FileInstallationStore(base_dir="./data")
)

# Initialize Slack app with OAuth
app = App(
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
    oauth_settings=oauth_settings
)

# Initialize Slack app
app = App(token=os.environ["SLACK_BOT_TOKEN"])

# Initialize MongoDB
mongo_client = MongoClient(os.environ["MONGODB_URI"])
db = mongo_client.chatbot
messages_collection = db.messages

# Initialize OpenAI
openai.api_key = os.environ["OPENAI_API_KEY"]

def store_message(channel_id: str, user_id: str, message: str, timestamp: str):
    """Store message in MongoDB"""
    messages_collection.insert_one({
        "channel_id": channel_id,
        "user_id": user_id,
        "message": message,
        "timestamp": timestamp,
        "created_at": datetime.now()
    })

def get_conversation_history(channel_id: str, limit: int = 5):
    """Retrieve last n messages from MongoDB"""
    return list(messages_collection
               .find({"channel_id": channel_id})
               .sort("timestamp", -1)
               .limit(limit))

def build_prompt(current_message: str, history: list) -> str:
    """Build prompt with conversation history"""
    prompt = "Previous conversation:\n"
    for msg in reversed(history):
        prompt += f"User: {msg['message']}\n"
    prompt += f"\nCurrent message: {current_message}\n"
    prompt += "\nPlease provide a helpful response to the current message, taking into account the context from previous messages if relevant."
    return prompt

def get_llm_response(prompt: str) -> str:
    """Get response from OpenAI API"""
    
    try:
        llm = ChatGroq(temperature=0, model_name="llama-3.3-70b-versatile")
        response = llm.invoke([
                {"role": "system", "content": "You are a helpful assistant in a Slack workspace."},
                {"role": "user", "content": prompt}
            ],
        )
        return response.content
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}"

@app.event("app_mention")
def handle_mention(event, say):
    """Handle mentions of the bot in channels"""
    try:
        # Extract message content (remove bot mention)
        message_text = event['text'].split(">", 1)[1].strip()
        
        # Store the current message
        store_message(
            channel_id=event['channel'],
            user_id=event['user'],
            message=message_text,
            timestamp=event['ts']
        )
        
        # Get conversation history
        history = get_conversation_history(event['channel'])
        
        # Build prompt with context
        prompt = build_prompt(message_text, history)
        
        # Get response from LLM
        response = get_llm_response(prompt)
        
        # Reply in thread
        say(text=response, thread_ts=event['ts'])
        
    except Exception as e:
        say(text=f"Sorry, I encountered an error: {str(e)}", thread_ts=event['ts'])

#if __name__ == "__main__":
print("Starting the app...")
handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
handler.start()