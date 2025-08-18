import configparser
from openai import OpenAI
from CalendarMeeting import CalendarMeeting
from datetime import datetime
import json

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
                            "date": "ISO 8601 datetime (e.g., 2025-08-04T17:00:00)",
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

# Example usage

meeting_statement = "Mohamed and Sama will meet on July 4, 2021 at 5pm in the office"
meeting = parse_meeting(
    client, meeting_statement
)
print(meeting)  

# response = client.chat.completions.create(
#     model="deepseek-chat",
#     messages=[
#         {"role": "system", "content": "You are a helpful assistant"},
#         {"role": "user", "content": "Hello"},
#     ],
#     stream=False
# )

# print(response.choices[0].message.content)