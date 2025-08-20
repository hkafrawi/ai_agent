"""
weather_ai_agent.py

This script demonstrates my understanding of building an AI agent that can use 
tools to answer user queries, specifically for fetching weather information.

I had to create a dedicated function to get a structured response 
using the DeepSeek API, which does not support the parse method.
"""


import configparser
from openai import OpenAI
import json
import requests
from pydantic import BaseModel, Field

config = configparser.ConfigParser()
config.read("config.ini")
deep_seek_api_key = config.get("API_KEYS", "openai_key")

client = OpenAI(api_key=deep_seek_api_key, base_url="https://api.deepseek.com")

# --------------------------------------------------------------
# Define the the classes and functions we need to use
# --------------------------------------------------------------

def get_structured_response(client_object, messages, model, tools, object_structure) -> BaseModel:
    """Generates a structured response from the AI model.
       This primarily for deep-seek-chat model, which does not
       support the parse method.
    Args:
        client_object: The OpenAI client object.
        messages: List of messages to send to the model.
        model: The model to use for generating the response.
        tools: List of tools available for the model to use.
        object_structure: Pydantic model defining the structure of the expected response."""

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

class WeatherResponse(BaseModel):
    temperature: float = Field(description="<float> - Current temperature in Celsius")
    response: str = Field(description="<string> A natural language response to the user's question.")

def call_function(name, args):
    if name == "get_weather":
        return get_weather(**args)
    
# --------------------------------------------------------------
# Step 1: Call model with get_weather tool defined
# --------------------------------------------------------------

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
    temperature=0.7
)

# --------------------------------------------------------------
# Step 2: Check if model decides to call function(s)
# --------------------------------------------------------------

print(completion.model_dump())
# We check whether the model has decided to use the get_weather function 
# and which parameters it has provided. 
#
# NB the AI agent does NOT call the function directly, we have to do that
# ourselves in the next step.

# --------------------------------------------------------------
# Step 3: Execute get_weather function
# --------------------------------------------------------------
    
for tool_call in completion.choices[0].message.tool_calls:
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    messages.append(completion.choices[0].message) 

    result = call_function(name, args) # This is where the function is called
    messages.append({
        "role": "tool",
        "content": json.dumps(result),
        "tool_call_id": tool_call.id  # Critical: Match the original call
    }) # We append the result of get_weather to the messages list to reask the model again

# --------------------------------------------------------------
# Step 4: Supply result and call model again
# --------------------------------------------------------------

final_completion = get_structured_response(
    client_object=client,
    messages=messages,
    model="deepseek-chat",
    tools=tools,
    object_structure=WeatherResponse
) # Reminder: This returns a WeatherResponse object

# --------------------------------------------------------------
# Step 5: Check model response
# --------------------------------------------------------------

print(final_completion.model_dump())   
