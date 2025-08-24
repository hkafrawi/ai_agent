"""
app.py

Using Streamlit to create a fast simple UI for my AI Agents

to run: write in terminal: streamlit run app.py
"""

import streamlit as st
from calender_meeting_ai_agent import parse_meeting, client

st.set_page_config(page_title="Meeting Parser Chat", page_icon="📅") #Set Tab Page 

st.title("📅 Meeting Parser Chat")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Display chat history
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and isinstance(msg["content"], dict):
            st.json(msg["content"])  # show parsed JSON nicely
        else:
            st.markdown(msg["content"])

# Input box at the bottom
if user_input := st.chat_input("Describe your meeting details..."):
    # Add user message to history
    st.session_state["messages"].append({"role": "user", "content": user_input})
    
    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(user_input)

    # Process with your parse_meeting function
    try:
        meeting = parse_meeting(client, user_input)
        meeting_json = meeting.model_dump()

        # Save assistant response
        st.session_state["messages"].append({"role": "assistant", "content": meeting_json})

        # Display assistant response
        with st.chat_message("assistant"):
            st.json(meeting_json)

    except Exception as e:
        error_msg = f"⚠️ Error: {e}"
        st.session_state["messages"].append({"role": "assistant", "content": error_msg})
        with st.chat_message("assistant"):
            st.error(error_msg)