"""
calender_meeting_ai_agent.py

In this script, i demonstrate my understanding of building an AI agent that can extract
information about calendar meetings from a user prompt using the DeepSeek API.

"""
import configparser
from openai import OpenAI
import json
from CalendarMeeting import CalendarMeeting
from datetime import datetime


config = configparser.ConfigParser()
config.read("config.ini")
deep_seek_api_key = config.get("API_KEYS", "openai_key")

client = OpenAI(api_key=deep_seek_api_key, base_url="https://api.deepseek.com")


def parse_meeting(client, user_prompt: str) -> CalendarMeeting:
    # Force JSON output via system prompt
    response = client.chat.completions.create(
        model="deepseek-chat",  # Use the correct model name
        messages=[
            {
                "role": "system",
                "content": """Extract meeting details and return STRICT JSON with these EXACT fields:
                        {
                            "date": "datetime",
                            "place": "meeting location",
                            "participants": ["list", "of", "names"]
                        }"""
            },
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"}, # Ensure response is in JSON format
        temperature = 1.0  
    )
    
    # Parse the JSON response
    try:
        json_str = response.choices[0].message.content
        data = json.loads(json_str)
        
        return CalendarMeeting(
            date=datetime.fromisoformat(data["date"]),
            place=data["place"],
            participants=data["participants"]
        )
    except (KeyError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to parse response: {e}")

# Example usage of parse_meeting function

meeting_statement = """Arthur and Nora were having lunch today with Mustafa. 
                    Mustafa said he will have a meeting on July 20,2025 
                    with Nora at 9pm in the office."""
meeting = parse_meeting(
    client, meeting_statement
)
print(meeting) 