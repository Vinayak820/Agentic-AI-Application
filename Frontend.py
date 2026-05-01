import queue
import uuid

import streamlit as st
from LanggraphBackend import chatbot, retrieve_all_threads, submit_async_task, ingest_pdf
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

# =========================== Utilities ===========================
def generate_thread_id():
    return str(uuid.uuid4())


def reset_chat():
    thread_id = generate_thread_id()
    st.session_state["thread_id"] = thread_id
    add_thread(thread_id)
    st.session_state["message_history"] = []


def add_thread(thread_id):
    thread_id = str(thread_id)
    if thread_id not in st.session_state["chat_threads"]:
        st.session_state["chat_threads"].append(thread_id)


def load_conversation(thread_id):
    state = chatbot.get_state(config={"configurable": {"thread_id": str(thread_id)}})
    return state.values.get("messages", [])


# ======================= Session Initialization ===================
if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()

if "chat_threads" not in st.session_state:
    st.session_state["chat_threads"] = retrieve_all_threads()

if "ingested_docs" not in st.session_state:
    st.session_state["ingested_docs"] = {}

add_thread(st.session_state["thread_id"])

thread_key = str(st.session_state["thread_id"])
thread_docs = st.session_state["ingested_docs"].setdefault(thread_key, {})

# ============================ Sidebar ============================
st.sidebar.title("Agentic AI Application")

if st.sidebar.button("New Chat"):
    reset_chat()

st.sidebar.header("My Conversations")

st.sidebar.markdown(f"Thread ID: `{thread_key}`")

# PDF status
if thread_docs:
    latest_doc = list(thread_docs.values())[-1]
    st.sidebar.success(
        f"Using {latest_doc.get('filename')} "
        f"({latest_doc.get('chunks')} chunks)"
    )
else:
    st.sidebar.info("No PDF uploaded yet")

# PDF uploader
uploaded_pdf = st.sidebar.file_uploader("Upload PDF", type=["pdf"])

if uploaded_pdf:
    if uploaded_pdf.name in thread_docs:
        st.sidebar.info(f"{uploaded_pdf.name} already uploaded")
    else:
        with st.sidebar.status("Indexing PDF...", expanded=True) as status_box:
            summary = ingest_pdf(
                uploaded_pdf.getvalue(),
                thread_id=str(thread_key),
                filename=uploaded_pdf.name,
            )

            thread_docs[uploaded_pdf.name] = summary

            status_box.update(
                label="PDF indexed",
                state="complete",
                expanded=False
            )

# ============================ Thread Switching ============================
for thread_id in st.session_state["chat_threads"][::-1]:
    if st.sidebar.button(str(thread_id)):

        st.session_state["thread_id"] = str(thread_id)

        messages = load_conversation(thread_id)

        temp_messages = []

        for msg in messages:

            # correct role detection
            if isinstance(msg, HumanMessage):
                role = "user"
            elif isinstance(msg, AIMessage):
                role = "assistant"
            else:
                continue  # skip ToolMessage

            content = msg.content

            # normalize content
            if isinstance(content, list):
                try:
                    content = " ".join(
                        item.get("text", "") for item in content if isinstance(item, dict)
                    )
                except:
                    content = str(content)

            # remove JSON/tool outputs
            if isinstance(content, str):
                stripped = content.strip()

                if stripped.startswith("{") or stripped.startswith("["):
                    continue

                if stripped.startswith("ERROR:"):
                    continue

            # remove blank messages
            if not content or not str(content).strip():
                continue

            temp_messages.append({
                "role": role,
                "content": content.strip()
            })

        st.session_state["message_history"] = temp_messages


# ============================ Main UI ============================

# render history
for message in st.session_state["message_history"]:

    if not message["content"] or not str(message["content"]).strip():
        continue

    with st.chat_message(message["role"]):
        st.text(message["content"])


user_input = st.chat_input("Type here")

if user_input:

    import LanggraphBackend
    LanggraphBackend.CURRENT_THREAD_ID = str(thread_key)

    st.session_state["message_history"].append({
        "role": "user",
        "content": user_input.strip()
    })

    with st.chat_message("user"):
        st.text(user_input)

    CONFIG = {
        "configurable": {"thread_id": str(thread_key)},
        "metadata": {"thread_id": str(thread_key)},
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

            collected_chunks = []

            while True:
                item = event_queue.get()
                if item is None:
                    break

                message_chunk, metadata = item

                if message_chunk == "error":
                    raise metadata

                # tool usage
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

                # AI response
                if isinstance(message_chunk, AIMessage):

                    content = message_chunk.content

                    if isinstance(content, list):
                        try:
                            content = " ".join(
                                item.get("text", "") for item in content if isinstance(item, dict)
                            )
                        except:
                            content = str(content)

                    if not content or not str(content).strip():
                        continue

                    collected_chunks.append(content)
                    yield content

            return "".join(collected_chunks)

        ai_message = st.write_stream(ai_only_stream())

        if status_holder["box"] is not None:
            status_holder["box"].update(
                label="Done",
                state="complete",
                expanded=False
            )

    # FINAL SAVE (no blank)
    if ai_message and isinstance(ai_message, str) and ai_message.strip():
        st.session_state["message_history"].append({
            "role": "assistant",
            "content": ai_message.strip()
        })