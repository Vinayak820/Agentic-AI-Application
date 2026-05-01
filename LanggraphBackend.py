from __future__ import annotations
from langgraph.graph import StateGraph, START, END
from typing import Annotated, Any, Dict, Optional, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool, BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv
import aiosqlite
import requests
import asyncio
import threading

# RAG
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
import os
import tempfile

load_dotenv()

CURRENT_THREAD_ID = None

# ---------------- ASYNC LOOP ----------------
_ASYNC_LOOP = asyncio.new_event_loop()
threading.Thread(target=_ASYNC_LOOP.run_forever, daemon=True).start()


def run_async(coro):
    """Run async coroutine in background loop and wait for result."""
    return asyncio.run_coroutine_threadsafe(coro, _ASYNC_LOOP).result()


def submit_async_task(coro):
    """Submit async task without blocking."""
    return asyncio.run_coroutine_threadsafe(coro, _ASYNC_LOOP)


# ---------------- LLM ----------------
llm = ChatOpenAI()
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")


# ---------------- RAG ----------------
_THREAD_RETRIEVERS: Dict[str, Any] = {}
_THREAD_METADATA: Dict[str, dict] = {}


def _get_retriever(thread_id: Optional[str]):
    """Return retriever for given thread if exists."""
    return _THREAD_RETRIEVERS.get(str(thread_id))


def ingest_pdf(file_bytes: bytes, thread_id: str, filename=None):
    """
    Build FAISS retriever from uploaded PDF and store per thread.

    Args:
        file_bytes: raw PDF bytes
        thread_id: chat thread id
        filename: original file name

    Returns:
        metadata about indexed document
    """

    if not file_bytes:
        raise ValueError("No PDF bytes received.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        f.write(file_bytes)
        path = f.name

    try:
        loader = PyPDFLoader(path)
        docs = loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )

        chunks = splitter.split_documents(docs)

        vector_store = FAISS.from_documents(chunks, embeddings)

        retriever = vector_store.as_retriever(
            search_kwargs={"k": 4}
        )

        thread_id = str(thread_id)

        # critical fix
        _THREAD_RETRIEVERS[thread_id] = retriever
        _THREAD_METADATA[thread_id] = {
            "filename": filename,
            "documents": len(docs),
            "chunks": len(chunks)
        }

        return _THREAD_METADATA[thread_id]

    finally:
        try:
            os.remove(path)
        except:
            pass


# ---------------- TOOLS ----------------
search_tool = DuckDuckGoSearchRun(region="us-en")


@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price using Alpha Vantage API.

    Example:
        AAPL, TSLA
    """
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=VGODPUQ3LFILAZCI"
    return requests.get(url).json()


client = MultiServerMCPClient(
    {
        "ExpenseTracker-Pro": {
            "transport": "stdio",
            "command": "python",
            "args": ["C:/Users/vinnu/OneDrive/Desktop/Agentic AI Application/main.py"],
        }
    }
)


def load_mcp_tools() -> list[BaseTool]:
    """Load tools from MCP server safely."""
    try:
        return run_async(client.get_tools())
    except Exception:
        return []


mcp_tools = load_mcp_tools()
print("Loaded MCP tools:", mcp_tools)


@tool
def rag_tool(query: str, thread_id: Optional[str] = None) -> str:
    """
    Answer questions from uploaded PDF only.
    """

    global CURRENT_THREAD_ID

    thread_id = str(thread_id or CURRENT_THREAD_ID)

    retriever = _get_retriever(thread_id)

    # clean fallback
    if retriever is None:
        return "NO_PDF"

    docs = retriever.invoke(query)

    context = "\n\n".join([d.page_content for d in docs])

    return f"""
    Context from PDF:
    {context}
    """


# ---------------- TOOL BIND ----------------
tools = [search_tool, get_stock_price, rag_tool, *mcp_tools]

llm_with_tools = llm.bind_tools(
    tools,
    tool_choice="auto"
)


# ---------------- STATE ----------------
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ---------------- CHAT NODE ----------------
async def chat_node(state: ChatState, config):
    """
    Main LLM node:
    - sets thread_id
    - injects system instruction
    - triggers tool usage
    """

    messages = state["messages"]

    thread_id = str(config.get("configurable", {}).get("thread_id"))

    global CURRENT_THREAD_ID
    CURRENT_THREAD_ID = thread_id

    system_msg = HumanMessage(content=f"""
    You are a helpful AI.

    Rules:

    1. Use rag_tool ONLY IF:
    - user clearly refers to uploaded PDF
    - OR asks about document content

    2. DO NOT use rag_tool if:
    - no PDF is uploaded
    - question is general (like story, coding, etc.)

    3. If rag_tool returns "NO_PDF":
    - answer normally using your own knowledge

    Always pass thread_id="{thread_id}" when calling tools.
    """)

    response = await llm_with_tools.ainvoke([system_msg] + messages)

    return {"messages": [response]}


tool_node = ToolNode(tools)


# ---------------- CHECKPOINTER ----------------
async def _init_checkpointer():
    conn = await aiosqlite.connect("chatbot.db")
    return AsyncSqliteSaver(conn)


checkpointer = run_async(_init_checkpointer())


# ---------------- GRAPH ----------------
graph = StateGraph(ChatState)

graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge("tools", "chat_node")

chatbot = graph.compile(checkpointer=checkpointer)


# ---------------- THREAD UTILS ----------------
async def _alist_threads():
    all_threads = set()
    async for checkpoint in checkpointer.alist(None):
        all_threads.add(checkpoint.config["configurable"]["thread_id"])
    return list(all_threads)


def retrieve_all_threads():
    return run_async(_alist_threads())