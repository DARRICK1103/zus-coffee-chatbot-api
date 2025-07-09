# agent/planner.py

import json
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough

# This file will now define the planner's LLM and chain
# The llm_for_planner will be passed from graph.py

# --- Planner Prompt Template ---
planner_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content="""You are a helpful AI assistant. Your goal is to determine the user's intent and decide the best course of action:
    - Call a tool (if applicable, output a tool call)
    - Directly answer the question (output a natural language response)
    - Ask for more information if the query is ambiguous or lacks necessary details (output a natural language response).

    Available tools and their descriptions:
    {tool_descriptions}

    --- Long-Term Conversation Summary (from your core memory) ---
    {long_term_summary}

    --- Retrieved Relevant Past Context (from broader knowledge/history) ---
    {retrieved_context_str}

    --- Conversation ---
    """),
    MessagesPlaceholder("messages"),
])

def planner_node(state: Dict, llm_for_planner: Any, tools_list: List[Any]) -> Dict:
    """
    Determines the user's intent and decides the next action (tool call or final answer).
    """
    messages = state["messages"]
    long_term_summary = state.get("long_term_summary", "No prior conversation summary available.")
    retrieved_context_list = state.get("retrieved_context", [])
    retrieved_context_str = "\n".join(retrieved_context_list) if retrieved_context_list else "No relevant past context found."

    print("\n--- Planner Node: Deciding next action ---")
    
    tool_descriptions_str = "\n".join([f"- {t.name}: {t.description}" for t in tools_list])

    # Create the planner chain using the provided llm_for_planner
    planner_chain = planner_prompt | llm_for_planner

    response = planner_chain.invoke({
        "messages": messages,
        "long_term_summary": long_term_summary,
        "retrieved_context_str": retrieved_context_str, # Renamed to match prompt
        "tool_descriptions": tool_descriptions_str
    })
    
    if response.tool_calls:
        print(f"Planner decided: TOOL CALL - {response.tool_calls}")
        return {
            "messages": [response], 
            "next_action_type": "tool_call",
            "intent": "tool_call_detected" # Keep intent for consistency if needed elsewhere
        }
    else:
        print(f"Planner decided: FINAL ANSWER or ASK FOR INFO - {response.content[:50]}...")
        return {
            "messages": [response], 
            "next_action_type": "final_answer",
            "intent": "chat" # Default to chat if no tool call
        }

