"""
Calendar_confirmation_aiagent.py

In this script, i demonstrate my understanding of prompt chaining when building AI agent.

"Prompt chaining decomposes a task into a sequence of steps, 
where each LLM call processes the output of the previous one."
source: (https://www.anthropic.com/engineering/building-effective-agents)
"""
import configparser
from datetime import datetime
from openai import OpenAI
import os
import logging
import json

config = configparser.ConfigParser()
config.read("config.ini")
deep_seek_api_key = config.get("API_KEYS", "openai_key")

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

client = OpenAI(api_key=deep_seek_api_key, base_url="https://api.deepseek.com")
model = "deepseek-chat"  

# --------------------------------------------------------------
# Step 1: Define the data models for each stage
# --------------------------------------------------------------

# Data model for the event extraction stage
EventExtractionModel = [{
    "name":"description",
    "description": "The raw description of the event to be extracted",
    "data_type": "string",
    "required": True},
    {"name":"is_calendar_event",
     "description": "Whether the description is a calendar event or not",
     "data_type": "boolean",
     "required": True},
     {"name":"confidence_score",
      "description": "LLM model confidence score of the event extraction",
      "data_type": "float",
      "required": True}
    ]

# Data Model for the calendar event details
EventDetailsModel = [{
    "name": "name_of_event",
    "description": "The name of the calendar event",
    "data_type": "string",
    "required": True
}, {
    "name": "date",
    "description": "Date and time of the event. Use ISO 8601 to format this value.",
    "data_type": "string",
    "required": True
}, {
    "name": "duration_minutes",
    "description": "duration of the event in minutes",
    "data_type": "int",
    "required": True
}, {
    "name": "participants",
    "description": "List of participants in the event",
    "data_type": "list[str]",
    "required": True
}]

# Data Model for confirmation message
ConfirmationMessageModel = [{
    "name": "confirmation_message",
    "description": "natural language confirmation message for the event",
    "data_type": "string",
    "required": True
}]

#function to print output from model
print_json = lambda data: print(json.dumps(data, indent=2))

def determine_event_extraction(user_input: str,data_structure = EventExtractionModel) -> json:
    """
    Step 1: Determine if the description is a calendar event.
    """
    logger.info("Starting event extraction analysis.")
    logger.debug(f"User input: {user_input}")

    today = datetime.now()
    date_context = f"Today's date is {today.strftime('%Y-%m-%d')}."


    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": f"""{date_context}. Analyze if the text describes a calendar event.
                always return a JSON object using the following format:
                {json.dumps(data_structure, indent=2)} \n
                the name describes the name of the key, the desctipion describes the value of the key, 
                the data_type describes the type of the value, 
                and required indicates whether the key is required or not. 
                """
            },
            {"role": "user", "content": user_input}
        ],
        response_format={"type": "json_object"},
        temperature=0.5
    )
    result = response.choices[0].message.content
    logger.info(
        f"Event extraction analysis completed. is Calendar Event: {result['is_calendar_event']}, Confidence Score: {result['confidence_score']}")
    
    return result