import openai
from dotenv import load_dotenv
import json
import time
import requests
import os
from bs4 import BeautifulSoup
import streamlit as st


load_dotenv()
client = openai.OpenAI()
model = "gpt-4o-mini"

def get_value_proposition(url):
    heading_tags = ["h1", "h2", "h3"]
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        title = [title.text for title in soup.find_all(heading_tags)]
        return title
    except Exception as e:
        print(e)

def create_assistant(url):
    assistant = client.beta.assistants.create(
        name="Ideal Customer Profil creator assistant",
        instructions="You are a Ideal Cutomer Profil (ICP) creator assistant.",
        tools=[
            {
                "type":"function",
                "function": {
                    "name":"get_value_proposition",
                    "description":"Get the value proposition for the given url",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "The URL of the company"
                            }
                        },
                        "required": ["url"]
                    }   
                }
            }
        ],
        model=model
    )

    thread = client.beta.threads.create()

    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=f"What is the ICP for this url: {url} in French please"
    )

    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant.id
    )

    wait_for_completion(thread,run)

def process_message(thread,run):
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    st.write(messages.data[0].content[0].text.value)
    # print(messages.data[0].content[0].text.value)

def call_required_functions(thread,run,required_actions):
    tool_outputs = []
    for action in required_actions:
        func_name = action.function.name
        arguments = json.loads(action.function.arguments)
        # print(f"Function name: {func_name}")
        # print(f"Arguments: {arguments}")
        if func_name == "get_value_proposition":
            headings = get_value_proposition(url=arguments["url"])
            headings_str = " ".join(heading + " " for heading in headings)
            print(headings_str)
            tool_outputs.append({
                "tool_call_id": action.id,
                "output": headings_str
            })

    print("Submitting outputs back to the Assistant...")       
    client.beta.threads.runs.submit_tool_outputs_and_poll(thread_id=thread.id, run_id=run.id, tool_outputs=tool_outputs)

def wait_for_completion(thread,run):
    if thread and run:
        while True:
            time.sleep(5)
            run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            print(run_status.status)
            if run_status.status == "completed":
                process_message(thread,run)
                # messages = client.beta.threads.messages.list(thread_id=thread.id)
                # print(messages.data[0].content[0].text.value)
                break
            elif run_status.status == "requires_action":
                call_required_functions(thread,run,required_actions = run.required_action.submit_tool_outputs.tool_calls)

def main():
    st.title("Ideal Customer Profil creator (ICP)")

    with st.form(key="user_input_form"):
        url = st.text_input("Enter url:")
        submit_button = st.form_submit_button(label="Run Assistant")

        if submit_button:
            create_assistant(url)


if __name__ == "__main__":
    main()
