import os
import streamlit as st
import ollama  # pip install ollama
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import datetime

# ---------------- Google Auth Helper ----------------
def create_service(client_secret_file, api_name, api_version, *scopes, prefix=''):
    CLIENT_SECRET_FILE = client_secret_file
    API_SERVICE_NAME = api_name
    API_VERSION = api_version
    SCOPES = list(scopes[0]) if len(scopes) == 1 and isinstance(scopes[0], (list, tuple)) else list(scopes)

    creds = None
    working_dir = os.getcwd()
    token_dir = 'token files'
    token_file = f'token_{API_SERVICE_NAME}_{API_VERSION}{prefix}.json'

    if not os.path.exists(os.path.join(working_dir, token_dir)):
        os.mkdir(os.path.join(working_dir, token_dir))

    if os.path.exists(os.path.join(working_dir, token_dir, token_file)):
        creds = Credentials.from_authorized_user_file(os.path.join(working_dir, token_dir, token_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(os.path.join(working_dir, token_dir, token_file), 'w') as token:
            token.write(creds.to_json())

    try:
        service = build(API_SERVICE_NAME, API_VERSION, credentials=creds)
        return service
    except Exception as e:
        st.error(f"Failed to create Google service: {e}")
        return None

# ---------------- Ollama Chat Helper ----------------
def run_agent(messages):
    try:
        response = ollama.chat(
            model="llama3",
            messages=messages
        )
        if "message" in response and "content" in response["message"]:
            return response["message"]["content"]
        return "⚠️ No response from AI model."
    except Exception as e:
        return f"⚠️ Ollama error: {e}"

# ---------------- Google Calendar Helper ----------------
def create_calendar_event(service, summary, start_dt, end_dt, timezone='America/New_York'):
    event = {
        'summary': summary,
        'start': {'dateTime': start_dt.isoformat(), 'timeZone': timezone},
        'end':   {'dateTime': end_dt.isoformat(), 'timeZone': timezone},
    }
    created_event = service.events().insert(calendarId='primary', body=event).execute()
    return created_event.get('htmlLink')

# ---------------- Streamlit App ----------------
st.title("Google Calendar AI Agent with Ollama (Free)")

# Load or initialize messages
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Enter your prompt here"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="⛹️"):
        st.markdown(prompt)

    with st.chat_message("ai", avatar="🤖"):
        # Run AI
        ai_response = run_agent(st.session_state.messages)
        st.markdown(ai_response)
        st.session_state.messages.append({"role": "assistant", "content": ai_response})

        # Check for simple "add event" command in AI response
        if "add event" in ai_response.lower() or "schedule" in ai_response.lower():
            service = create_service("credentials.json", "calendar", "v3", ["https://www.googleapis.com/auth/calendar"])
            if service:
                # Example: schedule tomorrow at 10am for 1 hour
                now = datetime.datetime.now()
                start = now + datetime.timedelta(days=1)
                start = start.replace(hour=10, minute=0, second=0, microsecond=0)
                end = start + datetime.timedelta(hours=1)

                event_link = create_calendar_event(service, "Meeting from AI Agent", start, end)
                st.success(f"✅ Event created: [Open in Google Calendar]({event_link})")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Event successfully created: {event_link}"
                })
