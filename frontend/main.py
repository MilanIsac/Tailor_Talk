import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "https://your-backend.onrender.com")

st.title("TailorTalk: Book your Appointment")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [("Bot", "Hello! How can I help you with booking or checking appointments?")]

user_input = st.text_input("You:", "")

if st.button("Send") and user_input:
    st.session_state.chat_history.append(("You", user_input))

    try:
        resp = requests.post(
            f"{BACKEND_URL}/chat",
            json={"message": user_input}
        )
        print("Frontend received status:", resp.status_code)
        print("Frontend received text:", resp.text)

        # Try to parse JSON response
        data = resp.json()
        response = data.get("response", "No response from bot.")
        
        if isinstance(response, dict) and "output" in response:
            response = response["output"]
        elif isinstance(response, dict) and "response" in response:
            response = response["response"]
            
    except Exception as e:
        print("Error:", e)
        response = "Sorry, there was an error communicating with the backend."

    st.session_state.chat_history.append(("Bot", response))

for sender, message in st.session_state.chat_history:
    st.write(f"**{sender}:** {message}")


# book an appointment to visit doctor at 3:00 pm to 4:00 pm at 03-07-2025