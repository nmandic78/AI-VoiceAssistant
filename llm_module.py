# llm_module.py

import openai
import threading

client = openai.OpenAI(
    base_url="http://127.0.0.1:8080/v1",  # "http://<Your api-server IP>:port"
    api_key="sk-no-key-required"
)

# Your existing request messages
conversation_history = []

# Thread lock for conversation history
history_lock = threading.Lock()

# Function to add a message to the conversation history
def add_message(role, content):
    with history_lock:
        conversation_history.append({"role": role, "content": content})

def clean_code_block(text: str) -> str:
    # Check if the string starts with ```
    if text.startswith("```"):
        # Remove everything until the first newline character
        text = text.split("\n", 1)[1]

    # Check if the string ends with ```
    if text.endswith("```"):
        text = text[:-3]

    # Remove any trailing newline characters
    return text.rstrip()

# Function to get a response from the OpenAI API
def get_response(query):
    add_message("user", query)
    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=conversation_history,
            temperature=0.5,
            max_tokens=1024,
            top_p=0.8
        )
        output = completion.choices[0].message.content
        answer = clean_code_block(output)
        add_message("assistant", answer)
        print('Conversation history: \n', conversation_history)
        return answer
    except Exception as e:
        print(f"[ERROR] LLM API call failed: {e}")
        return "I'm sorry, I couldn't process your request at this time."
