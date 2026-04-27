from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.message import add_messages

load_dotenv()

chatbot = ChatOpenAI(model="gpt-4-0613", temperature=0.7)

# Define the state of the graph
class GraphState(TypedDict):
    message : Annotated[list[BaseMessage], add_messages]

# Define the LLM response node
def llm_response(state:GraphState)->GraphState:
    messages = state["message"]
    response = chatbot.invoke(messages)
    return {"message": [response]}

# Initialize the graph
graph = StateGraph(GraphState)

# Add Nodes
graph.add_node("llm_response", llm_response)

# Add Edges
graph.add_edge(START, "llm_response")
graph.add_edge("llm_response", END)

# compile the graph
compiled_graph = graph.compile()

# invoke the graph
initial_state = {"message": [HumanMessage(content="What is the population of India?")]}
ai_message = compiled_graph.invoke(initial_state)

print("AI Response:", ai_message["message"][-1].content)