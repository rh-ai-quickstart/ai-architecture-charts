import os
from uuid import uuid4

from llama_stack.apis.common.content_types import URL
from ogx_client.lib.agents.agent import Agent
from ogx_client.lib.agents.event_logger import EventLogger as AgentEventLogger

LLAMA_STACK_ENDPOINT=os.getenv("LLAMA_STACK_ENDPOINT")
LLAMA_STACK_MODEL=os.getenv("LLAMA_STACK_MODEL")

print(f"LLAMA_STACK_ENDPOINT: {LLAMA_STACK_ENDPOINT}")
print(f"LLAMA_STACK_MODEL: {LLAMA_STACK_MODEL}")

from ogx_client import OgxClient
client = OgxClient(
    base_url=LLAMA_STACK_ENDPOINT
)

agent = Agent(
    client,
    model=LLAMA_STACK_MODEL,  
    instructions="You are a helpful assistant with access to a weather tool",  
    enable_session_persistence=False,
    tools=["mcp::weather"]
)

session_id = agent.create_session(f"test-session-{uuid4()}")

response = agent.create_turn(
    messages=[
        {
            "role": "user",
            "content": "what is the temperature in Raleigh?",
        }
    ],
    session_id=session_id,
)

print(f"Response: {response}")
print()
print()
for log in AgentEventLogger().log(response):
    log.print()
