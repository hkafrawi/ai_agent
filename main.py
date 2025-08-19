import configparser
from openai import OpenAI
from CalendarMeeting import CalendarMeeting
from datetime import datetime
import json
import requests
from pydantic import BaseModel, Field

config = configparser.ConfigParser()
config.read("config.ini")
deep_seek_api_key = config.get("API_KEYS", "openai_key")

client = OpenAI(api_key=deep_seek_api_key, base_url="https://api.deepseek.com")

# def parse_meeting(client, user_prompt: str) -> CalendarMeeting:
#     # Force JSON output via system prompt
#     response = client.chat.completions.create(
#         model="deepseek-chat",  # Use the correct model name
#         messages=[
#             {
#                 "role": "system",
#                 "content": """Extract meeting details and return STRICT JSON with these EXACT fields:
#                         {
#                             "date": "ISO 8601 datetime (e.g., 2025-08-04T17:00:00)",
#                             "place": "meeting location",
#                             "participants": ["list", "of", "names"]
#                         }"""
#             },
#             {"role": "user", "content": user_prompt}
#         ],
#         response_format={"type": "json_object"}, # Ensure response is in JSON format
#         temperature = 1.0  
#     )
    
#     # Parse the JSON response
#     try:
#         json_str = response.choices[0].message.content
#         data = json.loads(json_str)
        
#         return CalendarMeeting(
#             date=datetime.fromisoformat(data["date"]),
#             place=data["place"],
#             participants=data["participants"]
#         )
#     except (KeyError, json.JSONDecodeError) as e:
#         raise ValueError(f"Failed to parse response: {e}")

# # Example usage of parse_meeting function

# meeting_statement = "Arthur and Nora were having lunch today with Mustafa. Mustafa said he will have a meeting today with Nora at 9pm in the office."
# meeting = parse_meeting(
#     client, meeting_statement
# )
# print(meeting)  
def get_structured_response(client_object, messages, model, tools, object_structure) -> BaseModel:
    """Generates a structured response from the AI model."""

    field_descriptions = {
    name: field.description
    for name, field in object_structure.model_fields.items()
    }

    for item in messages:
        try:
            if item["role"] == "system":
                original_content = item["content"]
                item["content"] = f"""The following is your system prompt:
                                {original_content}
        
                                Ensure your response is in valid JSON format with these exact fields:
                                {field_descriptions}"""
                break
        except TypeError:
            continue

    response = client_object.chat.completions.create(
            model=model,  
            messages=messages,
            response_format={"type": "json_object"},
            tools=tools, 
            temperature = 1.0  
        )
    
    try:
        # print(response.model_dump())
        json_str = response.choices[0].message.content
        data = json.loads(json_str)

        structured_response = object_structure(**data)

        return structured_response
    except (KeyError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to parse response: {e}")
    

def get_weather(latitude, longitude):
    """This is a publically available API that returns the weather for a given location."""
    response = requests.get(
        f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,wind_speed_10m&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m"
    )
    data = response.json()
    return data["current"]

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather of an location, the user shoud supply a location first",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number",},
                    "longitude": {"type": "number",}
                },
                "required": ["latitude", "longitude"],
                "additionalProperties": False
            },
            "strict": True
        }
    }
]

system_prompt = """You are a helpful weather assistant. make sure to consider the following
- Get the latitude and longitude of the user's desired location from the internet. do not expect the user to provide latitude and longitude.
- If the user provides a location, use that location to get the latitude and longitude.
- use the get_weather tool to provide the current weather. 
- DO NOT reply back to user asking for more information.
- if the location provided is a large area, use the center of the area."""

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "What is the weather in Berlin today?"}]

completion = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    tools=tools,  # Automatically choose the best tool
    temperature=1.0
)

completion.model_dump()

def call_function(name, args):
    if name == "get_weather":
        return get_weather(**args)
    
for tool_call in completion.choices[0].message.tool_calls:
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    messages.append(completion.choices[0].message) 

    result = call_function(name, args)
    messages.append({
        "role": "tool",
        "content": json.dumps(result),
        "tool_call_id": tool_call.id  # Critical: Match the original call
    })


final_completion = get_structured_response(
    client_object=client,
    messages=messages,
    model="deepseek-chat",
    tools=tools,
    object_structure=WeatherResponse
)


# final_completion = client.chat.completions.create(
#     model="deepseek-chat",
#     messages=messages,
#     response_format={"type": "json_object"}  # Specify the response format
# )

print(type(final_completion))
print(final_completion)   
print(final_completion.model_dump())   
