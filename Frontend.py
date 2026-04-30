# # After MCP, with async streaming and better status handling

# import queue
# import uuid

# import streamlit as st
# from LanggraphBackend import chatbot, retrieve_all_threads, submit_async_task
# from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

# # =========================== Utilities ===========================
# def generate_thread_id():
#     return uuid.uuid4()


# def reset_chat():
#     thread_id = generate_thread_id()
#     st.session_state["thread_id"] = thread_id
#     add_thread(thread_id)
#     st.session_state["message_history"] = []


# def add_thread(thread_id):
#     if thread_id not in st.session_state["chat_threads"]:
#         st.session_state["chat_threads"].append(thread_id)


# def load_conversation(thread_id):
#     state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})
#     return state.values.get("messages", [])


# # ======================= Session Initialization ===================
# if "message_history" not in st.session_state:
#     st.session_state["message_history"] = []

# if "thread_id" not in st.session_state:
#     st.session_state["thread_id"] = generate_thread_id()

# if "chat_threads" not in st.session_state:
#     st.session_state["chat_threads"] = retrieve_all_threads()

# add_thread(st.session_state["thread_id"])

# # ============================ Sidebar ============================
# st.sidebar.title("LangGraph MCP Chatbot")

# if st.sidebar.button("New Chat"):
#     reset_chat()

# st.sidebar.header("My Conversations")
# for thread_id in st.session_state["chat_threads"][::-1]:
#     if st.sidebar.button(str(thread_id)):
#         st.session_state["thread_id"] = thread_id
#         messages = load_conversation(thread_id)

#         temp_messages = []
#         for msg in messages:
#             role = "user" if isinstance(msg, HumanMessage) else "assistant"

#             content = msg.content

#             # Fix MCP structured output
#             if isinstance(content, list):
#                 try:
#                     content = " ".join(
#                         item.get("text", "") for item in content if isinstance(item, dict)
#                     )
#                 except:
#                     content = str(content)

#             # Skip raw JSON
#             if isinstance(content, str) and content.strip().startswith("{") and "status" in content:
#                 continue

#             # Skip empty messages
#             if not content or not str(content).strip():
#                 continue

#             temp_messages.append({"role": role, "content": content})

#         st.session_state["message_history"] = temp_messages

# # ============================ Main UI ============================

# # Render history
# for message in st.session_state["message_history"]:
#     if not message["content"] or not str(message["content"]).strip():
#         continue

#     with st.chat_message(message["role"]):
#         st.text(message["content"])

# user_input = st.chat_input("Type here")

# if user_input:
#     st.session_state["message_history"].append({"role": "user", "content": user_input})
#     with st.chat_message("user"):
#         st.text(user_input)

#     CONFIG = {
#         "configurable": {"thread_id": st.session_state["thread_id"]},
#         "metadata": {"thread_id": st.session_state["thread_id"]},
#         "run_name": "chat_turn",
#     }

#     with st.chat_message("assistant"):
#         status_holder = {"box": None}

#         def ai_only_stream():
#             event_queue: queue.Queue = queue.Queue()

#             async def run_stream():
#                 try:
#                     async for message_chunk, metadata in chatbot.astream(
#                         {"messages": [HumanMessage(content=user_input)]},
#                         config=CONFIG,
#                         stream_mode="messages",
#                     ):
#                         event_queue.put((message_chunk, metadata))
#                 except Exception as exc:
#                     event_queue.put(("error", exc))
#                 finally:
#                     event_queue.put(None)

#             submit_async_task(run_stream())

#             while True:
#                 item = event_queue.get()
#                 if item is None:
#                     break

#                 message_chunk, metadata = item

#                 if message_chunk == "error":
#                     raise metadata

#                 # Ignore tool messages
#                 if isinstance(message_chunk, ToolMessage):
#                     continue

#                 if isinstance(message_chunk, AIMessage):
#                     content = message_chunk.content

#                     # Fix MCP structured output
#                     if isinstance(content, list):
#                         try:
#                             content = " ".join(
#                                 item.get("text", "") for item in content if isinstance(item, dict)
#                             )
#                         except:
#                             content = str(content)

#                     # Skip raw JSON
#                     if isinstance(content, str) and content.strip().startswith("{") and "status" in content:
#                         continue

#                     # Skip empty chunks
#                     if not content or not str(content).strip():
#                         continue

#                     yield content

#         ai_message = st.write_stream(ai_only_stream())

#     # Save only valid response
#     if ai_message and ai_message.strip():
#         st.session_state["message_history"].append(
#             {"role": "assistant", "content": ai_message}
#         )


# After MCP, with async streaming and better status handling

import queue
import uuid

import streamlit as st
from LanggraphBackend import chatbot, retrieve_all_threads, submit_async_task
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

# =========================== Utilities ===========================
def generate_thread_id():
    return uuid.uuid4()


def reset_chat():
    thread_id = generate_thread_id()
    st.session_state["thread_id"] = thread_id
    add_thread(thread_id)
    st.session_state["message_history"] = []


def add_thread(thread_id):
    if thread_id not in st.session_state["chat_threads"]:
        st.session_state["chat_threads"].append(thread_id)


def load_conversation(thread_id):
    state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})
    return state.values.get("messages", [])


# ======================= Session Initialization ===================
if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()

if "chat_threads" not in st.session_state:
    st.session_state["chat_threads"] = retrieve_all_threads()

add_thread(st.session_state["thread_id"])

# ============================ Sidebar ============================
st.sidebar.title("LangGraph MCP Chatbot")

if st.sidebar.button("New Chat"):
    reset_chat()

st.sidebar.header("My Conversations")
for thread_id in st.session_state["chat_threads"][::-1]:
    if st.sidebar.button(str(thread_id)):
        st.session_state["thread_id"] = thread_id
        messages = load_conversation(thread_id)

        temp_messages = []
        for msg in messages:
            role = "user" if isinstance(msg, HumanMessage) else "assistant"

            content = msg.content

            # Fix MCP structured output
            if isinstance(content, list):
                try:
                    content = " ".join(
                        item.get("text", "") for item in content if isinstance(item, dict)
                    )
                except:
                    content = str(content)

            # Skip raw JSON
            if isinstance(content, str) and content.strip().startswith("{") and "status" in content:
                continue

            # Skip empty messages
            if not content or not str(content).strip():
                continue

            temp_messages.append({"role": role, "content": content})

        st.session_state["message_history"] = temp_messages

# ============================ Main UI ============================

# Render history
for message in st.session_state["message_history"]:
    if not message["content"] or not str(message["content"]).strip():
        continue

    with st.chat_message(message["role"]):
        st.text(message["content"])

user_input = st.chat_input("Type here")

if user_input:
    st.session_state["message_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.text(user_input)

    CONFIG = {
        "configurable": {"thread_id": st.session_state["thread_id"]},
        "metadata": {"thread_id": st.session_state["thread_id"]},
        "run_name": "chat_turn",
    }

    with st.chat_message("assistant"):
        status_holder = {"box": None}

        def ai_only_stream():
            event_queue: queue.Queue = queue.Queue()

            async def run_stream():
                try:
                    async for message_chunk, metadata in chatbot.astream(
                        {"messages": [HumanMessage(content=user_input)]},
                        config=CONFIG,
                        stream_mode="messages",
                    ):
                        event_queue.put((message_chunk, metadata))
                except Exception as exc:
                    event_queue.put(("error", exc))
                finally:
                    event_queue.put(None)

            submit_async_task(run_stream())

            while True:
                item = event_queue.get()
                if item is None:
                    break

                message_chunk, metadata = item

                if message_chunk == "error":
                    raise metadata

                # ✅ Show tool usage (but hide raw output)
                if isinstance(message_chunk, ToolMessage):
                    tool_name = getattr(message_chunk, "name", "tool")

                    if status_holder["box"] is None:
                        status_holder["box"] = st.status(
                            f"Using {tool_name}...", expanded=True
                        )
                    else:
                        status_holder["box"].update(
                            label=f"Using {tool_name}...",
                            state="running",
                            expanded=True,
                        )
                    continue

                # ✅ Show only clean AI output
                if isinstance(message_chunk, AIMessage):
                    content = message_chunk.content

                    # Fix MCP structured output
                    if isinstance(content, list):
                        try:
                            content = " ".join(
                                item.get("text", "") for item in content if isinstance(item, dict)
                            )
                        except:
                            content = str(content)

                    # Skip raw JSON
                    if isinstance(content, str) and content.strip().startswith("{") and "status" in content:
                        continue

                    # Skip empty chunks
                    if not content or not str(content).strip():
                        continue

                    yield content

        ai_message = st.write_stream(ai_only_stream())

        # ✅ Mark tool complete
        if status_holder["box"] is not None:
            status_holder["box"].update(
                label="Done",
                state="complete",
                expanded=False
            )

    # Save only valid response
    if ai_message and ai_message.strip():
        st.session_state["message_history"].append(
            {"role": "assistant", "content": ai_message}
        )