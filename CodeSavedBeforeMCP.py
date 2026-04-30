# Frontend.py

# import streamlit as st
# from LanggraphBackend import chatbot, retrieve_all_threads
# from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
# import uuid

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
#     # Check if messages key exists in state values, return empty list if not
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
# st.sidebar.title("LangGraph Chatbot")

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
#             temp_messages.append({"role": role, "content": msg.content})
#         st.session_state["message_history"] = temp_messages

# # ============================ Main UI ============================

# # Render history
# for message in st.session_state["message_history"]:
#     with st.chat_message(message["role"]):
#         st.text(message["content"])

# user_input = st.chat_input("Type here")

# if user_input:
#     # Show user's message
#     st.session_state["message_history"].append({"role": "user", "content": user_input})
#     with st.chat_message("user"):
#         st.text(user_input)

#     CONFIG = {
#         "configurable": {"thread_id": st.session_state["thread_id"]},
#         "metadata": {"thread_id": st.session_state["thread_id"]},
#         "run_name": "chat_turn",
#     }

#     # Assistant streaming block
#     with st.chat_message("assistant"):
#         # Use a mutable holder so the generator can set/modify it
#         status_holder = {"box": None}

#         def ai_only_stream():
#             for message_chunk, metadata in chatbot.stream(
#                 {"messages": [HumanMessage(content=user_input)]},
#                 config=CONFIG,
#                 stream_mode="messages",
#             ):
#                 # Lazily create & update the SAME status container when any tool runs
#                 if isinstance(message_chunk, ToolMessage):
#                     tool_name = getattr(message_chunk, "name", "tool")
#                     if status_holder["box"] is None:
#                         status_holder["box"] = st.status(
#                             f"🔧 Using `{tool_name}` …", expanded=True
#                         )
#                     else:
#                         status_holder["box"].update(
#                             label=f"🔧 Using `{tool_name}` …",
#                             state="running",
#                             expanded=True,
#                         )

#                 # Stream ONLY assistant tokens
#                 if isinstance(message_chunk, AIMessage):
#                     yield message_chunk.content

#         ai_message = st.write_stream(ai_only_stream())

#         # Finalize only if a tool was actually used
#         if status_holder["box"] is not None:
#             status_holder["box"].update(
#                 label="✅ Tool finished", state="complete", expanded=False
#             )

#     # Save assistant message
#     st.session_state["message_history"].append(
#         {"role": "assistant", "content": ai_message}
#     )





# Backed.py
# from langgraph.graph import StateGraph, START, END
# from typing import TypedDict, Annotated
# from langchain_core.messages import BaseMessage, HumanMessage
# from langchain_openai import ChatOpenAI
# from langgraph.checkpoint.sqlite import SqliteSaver
# from langgraph.graph.message import add_messages
# from langgraph.prebuilt import ToolNode, tools_condition
# from langchain_community.tools import DuckDuckGoSearchRun
# from langchain_core.tools import tool
# from dotenv import load_dotenv
# import sqlite3
# import requests

# load_dotenv()

# # -------------------
# # 1. LLM
# # -------------------
# llm = ChatOpenAI()

# # -------------------
# # 2. Tools
# # -------------------
# # Tools
# search_tool = DuckDuckGoSearchRun(region="us-en")

# @tool
# def calculator(first_num: float, second_num: float, operation: str) -> dict:
#     """
#     Perform a basic arithmetic operation on two numbers.
#     Supported operations: add, sub, mul, div
#     """
#     try:
#         if operation == "add":
#             result = first_num + second_num
#         elif operation == "sub":
#             result = first_num - second_num
#         elif operation == "mul":
#             result = first_num * second_num
#         elif operation == "div":
#             if second_num == 0:
#                 return {"error": "Division by zero is not allowed"}
#             result = first_num / second_num
#         else:
#             return {"error": f"Unsupported operation '{operation}'"}
        
#         return {"first_num": first_num, "second_num": second_num, "operation": operation, "result": result}
#     except Exception as e:
#         return {"error": str(e)}


# @tool
# def get_stock_price(symbol: str) -> dict:
#     """
#     Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA') 
#     using Alpha Vantage with API key in the URL.
#     """
#     url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=VGODPUQ3LFILAZCI"
#     r = requests.get(url)
#     return r.json()


# tools = [search_tool, get_stock_price, calculator]
# llm_with_tools = llm.bind_tools(tools)

# # -------------------
# # 3. State
# # -------------------
# class ChatState(TypedDict):
#     messages: Annotated[list[BaseMessage], add_messages]

# # -------------------
# # 4. Nodes
# # -------------------
# def chat_node(state: ChatState):
#     """LLM node that may answer or request a tool call."""
#     messages = state["messages"]
#     response = llm_with_tools.invoke(messages)
#     return {"messages": [response]}

# tool_node = ToolNode(tools)

# # -------------------
# # 5. Checkpointer
# # -------------------
# conn = sqlite3.connect(database="chatbot.db", check_same_thread=False)
# checkpointer = SqliteSaver(conn=conn)

# # -------------------
# # 6. Graph
# # -------------------
# graph = StateGraph(ChatState)
# graph.add_node("chat_node", chat_node)
# graph.add_node("tools", tool_node)

# graph.add_edge(START, "chat_node")

# graph.add_conditional_edges("chat_node",tools_condition)
# graph.add_edge('tools', 'chat_node')

# chatbot = graph.compile(checkpointer=checkpointer)

# # -------------------
# # 7. Helper
# # -------------------
# def retrieve_all_threads():
#     all_threads = set()
#     for checkpoint in checkpointer.list(None):
#         all_threads.add(checkpoint.config["configurable"]["thread_id"])
#     return list(all_threads)


# # Will integrate in the frontend later, for now we can test the graph here in the backend
# # # invoke the graph
# # initial_state = {"message": [HumanMessage(content="What is the population of India?")]}
# # ai_message = chatbot.invoke(initial_state)
# # print("AI Response:", ai_message["message"][-1].content)