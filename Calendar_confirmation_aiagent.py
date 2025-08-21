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