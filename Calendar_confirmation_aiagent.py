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

data_model_descriptions = """
Always return a JSON object using the following format:
Below is the schema describing the fields.

Schema:
{schema_here}

### INSTRUCTIONS
- Use the `name` field as the key in the JSON output.  
- Generate a value according to its `description` and `data_type`.  
- Only include the keys (do not include `description`, `data_type`, or `required` in the output).  
- If `required` is false, return a null value for that key.  
- Your entire response must be a single valid JSON object, with no additional text, explanation, or Markdown formatting.  

### OUTPUT FORMAT (example)
{{
  "field1": <value>,
  "field2": <value>,
  ...
}}

"""

#function to print output from model
log_json = lambda data: logger.info(json.dumps(data, indent=2))

# --------------------------------------------------------------
# Step 2: Define the functions
# --------------------------------------------------------------

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
                {data_model_descriptions.format(schema_here=json.dumps(data_structure, indent=2))}  
                """
            },
            {"role": "user", "content": user_input}
        ],
        response_format={"type": "json_object"},
        temperature=0.5
    )
    result = response.choices[0].message.content
    logger.info("Event extraction analysis completed.")
    result = json.loads(result)
    log_json(result)
                
    
    return result

def extract_event_details(description: str, data_structure=EventDetailsModel) -> json:
    """
    Step 2: Extract details of the calendar event.
    """
    logger.info("Starting event details extraction.")
    logger.debug(f"Description: {description}")

    today = datetime.now()
    date_context = f"Today's date is {today.strftime('%Y-%m-%d')}."

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": f"""
                {date_context}.Extract the calendar event details from the text.
                If need be, use the current date as a reference.
                {data_model_descriptions.format(schema_here=json.dumps(data_structure, indent=2))}
                """
            },
            {"role": "user", "content": description}
        ],
        response_format={"type": "json_object"},
        temperature=0.5
    )
    
    result = response.choices[0].message.content
    logger.info("Event details extraction completed.")
    result = json.loads(result)
    log_json(result)
    
    return result

def generate_confirmation_message(event_details: json, data_structure=ConfirmationMessageModel) -> json:
    """
    Step 3: Generate a confirmation message for the calendar event.
    """
    logger.info("Starting confirmation message generation.")
    logger.debug(f"Event details: {json.dumps(event_details, indent=2)}")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": f"""Generate a natural language confirmation message for the calendar event.
                Sign of with your name; Bob
                {data_model_descriptions.format(schema_here=json.dumps(data_structure, indent=2))}
                """
            },
            {"role": "user", "content": str(json.dumps(event_details, indent=2))}
        ],
        response_format={"type": "json_object"},
        temperature=0.5
    )
    
    result = response.choices[0].message.content
    logger.info("Confirmation message generation completed.")
    result = json.loads(result)
    log_json(result)
    
    return result

# --------------------------------------------------------------
# Step 3: Chain the functions together
# --------------------------------------------------------------

def process_calendar_request(user_input: str) -> json:
    """
    Main function to process the calendar request.
    It chains the steps together to extract event details 
    and generate a confirmation message.
    """
    logger.info("Processing calendar request.")
    logger.debug(f"User input: {user_input}")
    
    # Step 1: Determine if the description is a calendar event
    event_extraction = determine_event_extraction(user_input)
    
    if (not event_extraction.get("is_calendar_event", False)
        or event_extraction.get("confidence_score", 0) < 0.7):
        logger.warning("The input does not describe a calendar event.")
        return None
    
    logger.info("Input is confirmed as a calendar event.")

    # Step 2: Extract details of the calendar event
    event_details = extract_event_details(event_extraction["description"])
    
    # Step 3: Generate a confirmation message for the calendar event
    confirmation_message = generate_confirmation_message(event_details)
    
    logger.info("Calendar request processing completed.")
    
    return confirmation_message

# --------------------------------------------------------------
# Step 3: Test the chain 
# --------------------------------------------------------------

# Valid calendar event request
user_input = "Let's schedule a 1h team meeting next Tuesday at 2pm with Said and Arthur to discuss the project roadmap. Mel doesnt need to attend"
result = process_calendar_request(user_input)
if result:
    logger.info(f"Confirmation: {result['confirmation_message']}")
else:
    logger.info(f"This doesn't appear to be a calendar event request.")

# Invalid calendar event request
user_input = "Can you send an email to Alice and Bob to discuss the project roadmap?"
result = process_calendar_request(user_input)
if result:
    logger.info(f"Confirmation: {result['confirmation_message']}")

else:
    logger.info("This doesn't appear to be a calendar event request.")