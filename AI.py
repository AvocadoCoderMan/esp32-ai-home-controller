"""
AI.py - LLM "brain" of the home assistant.

Takes one line of user text (from STT, later) and asks an LLM (Gemini via
OpenRouter) what to do. The model can answer in plain text or call tools:
  - trigger_smart_home: switch a device (calls runDevice.py)
  - save_memory / delete_memory: edit the persistent key-value memory (memory.json)

Chat history is stored in chatHistory.json and expires after 30 minutes.
Tool and device IDs come from AITools.json and the ESP32 Protocol.json.

Status: works standalone (see __main__ test). Not yet connected to main.py,
and the reply is only printed, not yet sent to TTS.
"""

'''
other AIs:
gemini-2.5-flash — best tool-call accuracy at low cost, fastest
gpt-4o-mini — what you have, totally fine
deepseek/deepseek-chat — cheapest, slightly less reliable on edge cases
'''


from openrouter import OpenRouter
import os, time, json, subprocess, random, threading
from dotenv import load_dotenv
from datetime import datetime
from audio_server import start_server


load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
HISTORY_FILE   = "chatHistory.json"
HISTORY_TTL    = 1800          # seconds (30 min)
HISTORY_MAX    = 20            # messages to keep
MODEL          = "google/gemini-2.5-flash"
TOOLS_FILE     = "AITools.json"

PROTOCOL_FILE = "ESP32Antenna/lib/Protocol/Protocol.json"
protocol={}
MEMORY_FILE ="memory.json"
memory={}

now = datetime.now().strftime("%A %d %B %Y, %H:%M")

# ── Load tools and protocol ────────────────────────────────────────────────────────────────
with open(TOOLS_FILE, "r") as f:
    my_tools = json.load(f)
with open(PROTOCOL_FILE, "r") as f:
    protocol = json.load(f)
with open(MEMORY_FILE) as f:
    memory = json.load(f)

# ── History management ────────────────────────────────────────────────────────
def load_history() -> list:
    """Return saved messages if they are younger than HISTORY_TTL, else []."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)
        if time.time() - data.get("last_updated", 0) < HISTORY_TTL:
            return data.get("messages", [])
        print("History is older than 30 mins — starting fresh.")
        with open(HISTORY_FILE, "w") as f:
            f.write("{}")
        return []
    except (json.JSONDecodeError, KeyError):
        print("History file corrupt — starting fresh.")
    return []


def save_history(messages: list) -> None:
    """Persist the last HISTORY_MAX messages with a timestamp."""
    payload = {
        "last_updated": time.time(),
        "messages": messages[-HISTORY_MAX:],
    }
    with open(HISTORY_FILE, "w") as f:
        json.dump(payload, f, indent=2)


# ── API helpers ───────────────────────────────────────────────────────────────
def _client():
    return OpenRouter(api_key=os.getenv("OPENROUTER_API_KEY"))


def send_message(history: list):
    SYSTEM_MESSAGE = {
    "role": "system",
    "content": (
        "You are a helpful home-assistant. "
        "Use the available tools to control devices when asked. "
        f"Current time: {now}"
        f"Your memory bank ({len(memory)}/25 entries): {json.dumps(memory)}. Never exceed 25 entries — delete the least relevant one before saving if full."
        f"If memory is full, delete the least relevant entry before saving a new one."
        "Keep replies concise and natural. "
        "When using a tool: put your spoken reply in the spoken_response field, leave it empty string if no reply is needed. "
        "When not using a tool: reply normally in the message content."
        f"Your personality seed for this session is {random.randint(1000,9999)}. Use it to vary your tone and examples."

    ),
}
    """Send the full conversation (system + history) and return the response."""
    with _client() as client:
        return client.chat.send(
            model=MODEL,
            tools=my_tools,
            messages=[SYSTEM_MESSAGE] + history,
            temperature=1.2
        )

def execAction(action_id):
    if(action_id=="corner_light_on"):
        subprocess.Popen(["python", "runDevice.py", protocol["MAC_CORNER_LAMP"], protocol["CODE_TURN_ON"]])
    elif action_id=="corner_light_off":
        subprocess.Popen(["python", "runDevice.py", protocol["MAC_CORNER_LAMP"], protocol["CODE_TURN_OFF"]])
    #TODO: 
    """ elif action_id=="desk_power_off":
      subprocess.Popen(["python", "runDevice.py", protocol["MAC_DESK_POWER"], protocol["CODE_TURN_OFF"]])
    elif action_id=="desk_power_on":
      subprocess.Popen(["python", "runDevice.py", protocol["MAC_DESK_POWER"], protocol["CODE_TURN_ON"]]) """


# ── Single-shot handler ───────────────────────────────────────────────────────
def handle(user_input: str) -> None:
    chat_history = load_history()
    chat_history.append({"role": "user", "content": user_input})
    with open("memory.json", "r") as f:
                            mem = json.load(f)
    try:
        response = send_message(chat_history)
        message  = response.choices[0].message
        # ── Tool-use branch ───────────────────────────────────────────────────
        if getattr(message, "tool_calls", None):
            reply_text = ""
            
            # Record assistant turn first (contains all tool calls)
            chat_history.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [{
                    "id":       tc.id,
                    "type":     "function",
                    "function": {
                        "name":      tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                } for tc in message.tool_calls],  # all of them
            })

            for tool_call in message.tool_calls:  # loop instead of [0]
                action_data = json.loads(tool_call.function.arguments)
                tool_name   = tool_call.function.name

                if tool_name == "trigger_smart_home":
                    reply_text = action_data["spoken_response"]
                    print(f"[SMART HOME] Action triggered: {action_data['action_id']}")
                    execAction(action_data["action_id"])

                elif tool_name == "save_memory":
                    with open("memory.json", "r") as f:
                        mem = json.load(f)
                    mem[action_data["key"]] = action_data["value"]
                    with open("memory.json", "w") as f:
                        json.dump(mem, f, indent=2)
                    print(f"[MEMORY] Saved: {action_data['key']} = {action_data['value']}")
                
                elif tool_name == "delete_memory":
                    mem.pop(action_data["key"], None)  # None = no crash if key doesn't exist
                    with open("memory.json", "w") as f:
                        json.dump(mem, f, indent=2)
                    print(f"[MEMORY] Deleted: {action_data['key']}")

                # Each tool call needs its own result entry
                chat_history.append({
                    "role":         "tool",
                    "tool_call_id": tool_call.id,
                    "content":      json.dumps({"success": True}),
                })

            if reply_text.strip():
                print(f"Assistant: {reply_text}")
                chat_history.append({"role": "assistant", "content": reply_text})
        else:
            reply = message.content or ""
            print(f"Assistant: {reply}")
            chat_history.append({"role": "assistant", "content": reply})

    except Exception as e:
        print(f"[ERROR] {e}")
        chat_history.pop()  # drop the user message so history stays clean

    finally:
        save_history(chat_history)


if __name__ == "__main__":
    handle("turn the desk on and the lights too pls")