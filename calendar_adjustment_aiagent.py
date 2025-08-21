"""
Calendar_adjustment_aiagent.py

In this script, i demonstrate my understanding of routing when building AI agent.

"Routing classifies an input and directs it to a specialized followup task. 
This workflow allows for separation of concerns, and building more specialized prompts. 
Without this workflow, optimizing for one kind of input can hurt performance 
on other inputs."
source: (https://www.anthropic.com/engineering/building-effective-agents)
"""
import configparser
from datetime import datetime
from openai import OpenAI
import os
import logging
import json
import sqlite3

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
# Data Models
# --------------------------------------------------------------


CalendarRequestTypeModel = [{
    "name": "request_type",
    "description": "Type of calendar request, e.g., 'create', 'update', 'other'",
    "data_type": "Literal['create', 'update', 'other']",
    "required": True
}, {
    "name": "confidence_score",
    "description": "LLM model confidence score between 0 and 1 for the request type classification",
    "data_type": "int",
    "required": True
}, {
    "name": "description",
    "description": "Cleaned description of the request",
    "data_type": "string",
    "required": True
}]

CreateEventModel = [{
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
    "name": "duration",
    "description": "duration of the event in minutes",
    "data_type": "int",
    "required": True
}, {
    "name": "participants",
    "description": "List of participants for the event, if applicable",
    "data_type": "List[str]",
    "required": False
}]

RequestedChangeModel = [{
    "name": "field_to_update",
    "description": "name of the field to be updated in the event, e.g., 'date', 'participants', 'name_of_event'",
    "data_type": "string",
    "required": True
}, {
    "name": "new_value",
    "description": "new value for the field to be updated",
    "data_type": "match the field_to_update data type",
    "required": True
}]

UpdateEventModel = [{
    "name": "name_of_event",
    "description": "description of the existing event to be updated",
    "data_type": "string",
    "required": True
}, {
    "name": "requested_changes",
    "description": "List of requested changes to the event",
    "data_type": "List[RequestedChangeModel] ie. list of dictionaries",
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


# --------------------------------------------------------------
# Supporting functions
# --------------------------------------------------------------
#function to print output from model
log_json = lambda data: logger.info(json.dumps(data, indent=2))

def access_database_for_events(query: str = None):
    if query == None:
        conn = sqlite3.connect('calender.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM calender_events")
        rows = cursor.fetchall()
        conn.close()
        return rows

    conn = sqlite3.connect('calender.db')
    cursor = conn.cursor()

    logger.info("Executing query: %s", query)
    cursor.execute(query)
    conn.commit()

    cursor.execute("SELECT * FROM calender_events")
    logger.info("Query executed successfully. Fetching results...")
    for row in cursor.fetchall():
        logger.info(row)
    conn.close()



def call_function(name, args):
    if name == "access_database_for_events":
        return access_database_for_events(**args)



# --------------------------------------------------------------
# Routing and processing functions
# --------------------------------------------------------------

def determine_calendar_request(user_input: str) -> json:
    """
    Determins the calendar request type.
    """

    logger.info("Determining calendar request type...")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": f"""Determine if this is a request to create a new calendar event 
                or modify an existing one. \n
                {data_model_descriptions.format(
                    schema_here=json.dumps(CalendarRequestTypeModel, indent=2))}""",
            },
            {
                "role": "user",
                "content": user_input,
            },
        ],
        response_format={"type": "json_object"})

    result = response.choices[0].message.content
    result = json.loads(result)
    logger.info("Calendar request type determination completed.")
    log_json(result)

    return result


def create_new_event(description:str) -> json:
    """
    Create a new calendar event based on the provided description.
    """

    logger.info("Creating new calendar event...")

    tools = [
    {
        "type": "function",
        "function": {
            "name": "access_database_for_events",
            "description": """Access the sqlite database with a query to fulfill a request.
            - There is only one table in the database called calender_events.
            - The table has the following columns: name_of_event, date, duration, participants.
            - Use INSERT INTO to add a new calandar event.
            - Use UPDATE to modify an existing calendar event.
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    }
    ]

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": f"""Extract details for creating a new calendar event. 
                \n{data_model_descriptions.format(
                    schema_here=json.dumps(CreateEventModel, indent=2))}""",
            },
            {"role": "user","content": description},
        ],
        response_format={"type": "json_object"}
    )

    result = response.choices[0].message.content
    result = json.loads(result)

    logger.info("Calendar event details extracted...")

    messages = [
            {
                "role": "system",
                "content": f"""Insert the new calendar event into the database using the following query format:
                \nINSERT INTO calender_events (name_of_event, date, duration_minutes, participants) 
                """,
            },
            {"role": "user","content": json.dumps(result, indent=2)},
        ]
    response2 = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,  # Automatically choose the best tool
        temperature=0.7
    )

    for tool_call in response2.choices[0].message.tool_calls:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        messages.append(response2.choices[0].message) 

        result = call_function(name, args) # This is where the function is called
        messages.append({
            "role": "tool",
            "content": json.dumps(result),
            "tool_call_id": tool_call.id  # Critical: Match the original call
        })

    logger.info("New calendar event created successfully.")

def update_event(description:str) -> json:
    """
    update existing calendar event based on the provided description.
    """

    logger.info("Updating existing calendar event...")

    tools = [
    {
        "type": "function",
        "function": {
            "name": "access_database_for_events",
            "description": """Access the sqlite database with a query to fulfill a request.
            - There is only one table in the database called calender_events.
            - The table has the following columns: name_of_event, date, duration, participants.
            - Use INSERT INTO to add a new calandar event.
            - Use UPDATE to modify an existing calendar event.
            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    }
    ]
    current_events = json.dumps(access_database_for_events(), indent=2)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": f"""Extract details for updating an existing calendar event. 
                \n{data_model_descriptions.format(
                    schema_here=json.dumps(UpdateEventModel, indent=2))}
                \n
                The `requested_changes` field should be a list of dictionaries, each containing:
                \n{json.dumps(RequestedChangeModel, indent=2)}
                \n - Make sure that the field_to_update in the `requested_changes` field matches the column names in the database.
                \n - Make sure that the new_value in the `requested_changes` field matches the data type of the column in the database.
                \n - Combine date and time into a single string in ISO 8601 format when required.
                \n - Note that result will be used to update the database calender_events which has a schema as follows:
                \n name_of_event TEXT NOT NULL, date TEXT NOT NULL, duration_minutes INTEGER NOT NULL, participants TEXT NOT NULL
                \n The current rows in the database are as follows for reference:
                \n {current_events}
                """,
            },
            {"role": "user","content": description},
        ],
        response_format={"type": "json_object"}
    )

    result = response.choices[0].message.content
    result = json.loads(result)

    logger.info("Calendar event Update details extracted...")
    log_json(result)

    messages = [
            {
                "role": "system",
                "content": f"""Update the calendar event in the database using the following query format:
                \n UPDATE calender_events SET '...' = '...', '...' = '...' WHERE name_of_event = '...'
                \n - Note that the schema for calender_events is as follows:
                \n name_of_event TEXT NOT NULL, date TEXT NOT NULL, duration_minutes INTEGER NOT NULL, participants TEXT NOT NULL
                \n - Update the event in one single query.
                \n - Use tool calls to access the database.
                \n - You dont need to know the current parameters of the event, just update the event with the new parameters provided.
                \n - Use the `name_of_event` field to identify the event to be updated.
                """,
            },
            {"role": "user","content": json.dumps(result, indent=2)},
        ]
    response2 = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools
    )

    logger.info(response2.model_dump())

    for tool_call in response2.choices[0].message.tool_calls:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        messages.append(response2.choices[0].message) 

        result = call_function(name, args) # This is where the function is called
        messages.append({
            "role": "tool",
            "content": json.dumps(result),
            "tool_call_id": tool_call.id  # Critical: Match the original call
        })

    logger.info("Calender event updated successfully.")

def process_calendar_request(user_input: str):
    """
    Main function implementing the routing workflow
    """
    logger.info("Processing calendar request")

    # Route the request
    route_result = determine_calendar_request(user_input)

    # Check confidence threshold
    if route_result["confidence_score"] < 0.7:
        logger.warning(f"Low confidence score: {route_result['confidence_score']}")
        return None

    # Route to appropriate handler
    if route_result["request_type"] == "create":
        return create_new_event(route_result["description"])
    elif route_result["request_type"] == "update":
        return update_event(route_result["description"])
    else:
        logger.warning("Request type not supported")
        return None
    
    
# --------------------------------------------------------------
# Tests
# --------------------------------------------------------------

new_event_input = "Let's schedule a team lunch next Tuesday at 2pm with Nada and Sana"
result = process_calendar_request(new_event_input)

modify_event_input = (
    "Can you move the team meeting with Alice, Bob and Charlie to Wednesday at 3pm instead?"
)
result = process_calendar_request(modify_event_input)


invalid_input = "What's the weather like today?"
result = process_calendar_request(invalid_input)

