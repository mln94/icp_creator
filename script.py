import openai
from dotenv import load_dotenv
import json
import time
import requests
import os
from bs4 import BeautifulSoup


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
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["Celsius", "Farhenheit"],
                            "description": "The temperature unit to use. Infer this from the user's location."
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
    content=f"What is the ICP for this url: https://www.deluj.com "
)

run = client.beta.threads.runs.create_and_poll(
    thread_id=thread.id,
    assistant_id=assistant.id
)

def process_message():
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    print(messages.data[0].content[0].text.value)

def call_required_functions(required_actions):
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

def wait_for_completion():
    if thread and run:
        while True:
            time.sleep(5)
            run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            print(run_status.status)
            if run_status.status == "completed":
                process_message()
                # messages = client.beta.threads.messages.list(thread_id=thread.id)
                # print(messages.data[0].content[0].text.value)
                break
            elif run_status.status == "requires_action":
                call_required_functions(required_actions = run.required_action.submit_tool_outputs.tool_calls)

wait_for_completion()
