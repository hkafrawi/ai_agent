"""
ecommerce_assistant_aiagent.py

In this script, i demonstrate my understanding of building an AI agent that can retrieve
information from a database or databank to answer user prompt.

"""
import configparser

import json
import os

from openai import OpenAI
from pydantic import BaseModel, Field

config = configparser.ConfigParser()
config.read("config.ini")
deep_seek_api_key = config.get("API_KEYS", "openai_key")

client = OpenAI(api_key=deep_seek_api_key, base_url="https://api.deepseek.com")

# --------------------------------------------------------------
# Define the knowledge base retrieval tool
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

def load_kb(question: str):
    """
    Load the whole knowledge base from the JSON file.
    """
    with open("kb.json", "r") as f:
        return json.load(f)


# --------------------------------------------------------------
# Step 1: Call model with search_kb tool defined
# --------------------------------------------------------------

tools = [
    {
        "type": "function",
        "function": {
            "name": "load_kb",
            "description": "Get the answer to the user's question from the knowledge base.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                },
                "required": ["question"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    }
]

system_prompt = "You are a helpful assistant that answers questions from the knowledge base about our e-commerce store."

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "What is the return policy?"},
]

completion = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    tools=tools,
)

# --------------------------------------------------------------
# Step 2: Model decides to call function(s)
# --------------------------------------------------------------
print(f"\n")
print(completion.model_dump())

# --------------------------------------------------------------
# Step 3: Execute search_kb function
# --------------------------------------------------------------


def call_function(name, args):
    if name == "load_kb":
        return load_kb(**args)


for tool_call in completion.choices[0].message.tool_calls:
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    messages.append(completion.choices[0].message)

    result = call_function(name, args)
    messages.append(
        {"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)}
    )

# --------------------------------------------------------------
# Step 4: Supply result and call model again
# --------------------------------------------------------------


class KBResponse(BaseModel):
    answer: str = Field(description="The answer to the user's question.")
    source: int = Field(description="The record id of the answer.")


final_completion = get_structured_response(
    client_object=client,
    messages=messages,
    model="deepseek-chat",
    tools=tools,
    object_structure=KBResponse
)

# --------------------------------------------------------------
# Step 5: Check model response
# --------------------------------------------------------------
print(f"\n")
print(final_completion.model_dump())

# --------------------------------------------------------------
# Question that doesn't trigger the tool?
# --------------------------------------------------------------

# returns error, must create try except block to handle this
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "What is the weather in Tokyo?"},
]

final_completion_2 = get_structured_response(
    client_object=client,
    messages=messages,
    model="deepseek-chat",
    tools=tools,
    object_structure=KBResponse
)
print(f"\n")
print(final_completion_2.model_dump())