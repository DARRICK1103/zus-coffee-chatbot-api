import os
import sqlite3
from dotenv import load_dotenv
from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
from typing import Annotated, TypedDict, List, Union

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.utils.function_calling import convert_to_openai_tool

# Load environment
load_dotenv()

# Define Graph State
class GraphState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    long_term_summary: str
    retrieved_context: List[str]
    intent: str # This is from your original planner, but now we use next_action_type
    next_action_type: str # Added for conditional edges
    slots: dict # for tracking follow-up slots (e.g., missing branch, product) - if you still use this

# Import nodes (ensure these paths are correct relative to graph.py)
from agent.memory import manage_memory_node, retrieve_long_term_memory_node, summary_chain, main_chat_chain, vectorstore, MAX_RECENT_MESSAGES, MESSAGES_TO_SUMMARIZE_PER_BATCH
# --- UPDATED: Import planner_node from agent.planner ---
from agent.planner import planner_node 
from agent.nodes.product_tool import get_product_info 
from agent.nodes.outlet_tool import get_outlet_details 

# --- Define Tools (as they are used by the planner_node) ---
@tool
def calculator(expression: str) -> str:
    """Calculates the result of a mathematical expression.
    Input should be a string representing the expression, e.g., '2 + 2 * 3'.
    """
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Error: Could not calculate '{expression}'. Please provide a valid mathematical expression. Details: {e}"


# Combine all tools, including your new API-backed tools
tools = [calculator, get_product_info, get_outlet_details]
openai_tools = [convert_to_openai_tool(tool_func) for tool_func in tools]

# LLM for planner (needs to be able to use tools)
llm_for_planner = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools(openai_tools)

# --- Tool Executor Node (UPDATED to pass memory) ---
def tool_executor_node(state: GraphState) -> GraphState:
    messages = state["messages"]
    last_ai_message = messages[-1] 

    if not last_ai_message.tool_calls:
        print("ERROR: tool_executor_node called, but last AI message has no tool_calls.")
        return {"messages": [AIMessage(content="An internal error occurred: No tool calls found.")]}

    tool_results_messages = []
    
    print("\n--- Tool Executor Node: Executing Tool Calls ---")

    long_term_summary = state.get("long_term_summary", "")
    retrieved_context = state.get("retrieved_context", [])

    for tool_call in last_ai_message.tool_calls:
        tool_name = tool_call['name']
        tool_args = tool_call['args']
        tool_call_id = tool_call['id']

        print(f"Executing tool '{tool_name}' (ID: {tool_call_id}) with args: {tool_args}")

        tool_to_run = next((t for t in tools if t.name == tool_name), None)

        if tool_to_run:
            try:
                import inspect
                tool_signature = inspect.signature(tool_to_run.func)
                
                actual_tool_args = tool_args.copy()
                if 'long_term_summary' in tool_signature.parameters:
                    actual_tool_args['long_term_summary'] = long_term_summary
                if 'retrieved_context' in tool_signature.parameters:
                    actual_tool_args['retrieved_context'] = retrieved_context

                tool_result = tool_to_run.invoke(actual_tool_args)
                print(f"Tool '{tool_name}' executed. Result: {tool_result[:100]}...")
                tool_results_messages.append(ToolMessage(
                    content=tool_result, 
                    tool_call_id=tool_call_id 
                ))
            except Exception as e:
                print(f"ERROR: Failed to execute tool '{tool_name}' (ID: {tool_call_id}): {e}")
                tool_results_messages.append(ToolMessage(
                    content=f"Error executing tool '{tool_name}': {e}",
                    tool_call_id=tool_call_id
                ))
        else:
            print(f"ERROR: Tool '{tool_name}' (ID: {tool_call_id}) not found.")
            tool_results_messages.append(ToolMessage(
                content=f"Tool '{tool_name}' was requested but not found or not callable.",
                tool_call_id=tool_call_id
            ))
            
    return {"messages": tool_results_messages}

# --- Chat Response Generator Node (UPDATED to use memory) ---
def chat_response_generator_node(state: GraphState):
    messages = state["messages"]
    long_term_summary = state.get("long_term_summary", "No prior conversation summary available.")
    retrieved_context_list = state.get("retrieved_context", [])
    retrieved_context_str = "\n".join(retrieved_context_list) if retrieved_context_list else "No relevant past context found."

    context_for_llm = {
        "messages": messages, 
        "long_term_summary": long_term_summary,
        "retrieved_context": retrieved_context_str
    }
    
    print("\n--- Chat Node: Generating final user-facing response ---")
    response = main_chat_chain.invoke(context_for_llm)
    
    return {"messages": [response]} 

# Define graph
graph = StateGraph(GraphState)

# Add core nodes
graph.add_node("manage_memory", manage_memory_node)
graph.add_node("retrieve_memory", retrieve_long_term_memory_node)
# --- UPDATED: Pass llm_for_planner and tools to planner_node ---
graph.add_node("planner", lambda state: planner_node(state, llm_for_planner, tools))

# Tool executor and chat response generator
graph.add_node("tool_executor", tool_executor_node)
graph.add_node("chat_response_generator", chat_response_generator_node)

# Define flow
graph.set_entry_point("manage_memory")
graph.add_edge("manage_memory", "retrieve_memory")
graph.add_edge("retrieve_memory", "planner") 

graph.add_conditional_edges(
    "planner", 
    lambda state: state["next_action_type"], 
    {
        "tool_call": "tool_executor",       
        "final_answer": "chat_response_generator" 
    }
)

graph.add_edge("tool_executor", "chat_response_generator")

graph.set_finish_point("chat_response_generator")

# SQLite checkpoint setup
memory_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chatbot_memory")
os.makedirs(memory_dir, exist_ok=True)
conn = sqlite3.connect(os.path.join(memory_dir, "agent_chat.sqlite"), check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

# Compile app
app = graph.compile(checkpointer=checkpointer)

if __name__ == "__main__":
    print("💬 Chat started. Type 'exit' to quit.\n")
    thread_id = "user-darrick"

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        try:
            res = app.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                config={"configurable": {"thread_id": thread_id}}
            )
            reply = res["messages"][-1]
            print("🤖", reply.content)

        except Exception as e:
            print("❌ Error:", str(e))
            import traceback
            traceback.print_exc()
            break

    conn.close()
