from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

llm = ChatOpenAI(model="gpt-4-0613", temperature=0.7)

# Define the state of the graph
class GraphState(TypedDict):
    message : Annotated[list[BaseMessage], add_messages]

# Define the LLM response node
def llm_response(state:GraphState)->GraphState:
    messages = state["message"]
    response = llm.invoke(messages)
    return {"message": [response]}

# Initialize the graph
graph = StateGraph(GraphState)

checkpoint_saver = InMemorySaver()

# Add Nodes
graph.add_node("llm_response", llm_response)

# Add Edges
graph.add_edge(START, "llm_response")
graph.add_edge("llm_response", END)

# compile the graph
chatbot = graph.compile(checkpointer=checkpoint_saver)



# Will integrate in the frontend later, for now we can test the graph here in the backend
# # invoke the graph
# initial_state = {"message": [HumanMessage(content="What is the population of India?")]}
# ai_message = chatbot.invoke(initial_state)
# print("AI Response:", ai_message["message"][-1].content)