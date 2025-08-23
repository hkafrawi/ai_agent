"""
app.py

Using Streamlit to create a fast simple UI for my AI Agents

to run: write in terminal: streamlit run app.py
"""

import streamlit as st
from calender_meeting_ai_agent import parse_meeting, client

st.title("📅 Meeting Parser")
user_prompt = st.text_area("Enter meeting details:")

if st.button("Parse Meeting"):
    try:
        meeting = parse_meeting(client, user_prompt)
        st.json(meeting.model_dump())  # Nicely formatted JSON
    except Exception as e:
        st.error(f"Error: {e}")
