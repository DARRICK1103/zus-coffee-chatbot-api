# agent/nodes/outlet_tool.py

import requests
from langchain_core.tools import tool
from typing import Dict, Any, List
import json # Ensure json is imported for the tool's internal use

@tool
def get_outlet_details(query: str, long_term_summary: str = "", retrieved_context: List[str] = []) -> str:
    """
    Retrieves information about ZUS Coffee outlets, including their location,
    hours, and services. Use this tool for questions about specific outlets,
    their address, opening times, or available services.
    
    Args:
        query (str): The natural language query about ZUS Coffee outlets.
        long_term_summary (str): A summary of the ongoing conversation.
        retrieved_context (List[str]): Relevant past conversation segments or documents.
    """
    print(f"TOOL CALL: Calling /outlets endpoint with query: '{query}'")
    
    params = {
        "query": query,
        "long_term_summary": long_term_summary,
        "retrieved_context": json.dumps(retrieved_context) # Pass list as JSON string
    }

    try:
        resp = requests.get("http://localhost:8000/outlets", params=params, timeout=10)
        resp.raise_for_status()
        data: Dict[str, Any] = resp.json()

        response_text = data.get("query_response", "Sorry, I couldn’t find that outlet info.")
        
        print(f"TOOL RESPONSE: /outlets returned: {response_text[:100]}...")
        return response_text
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to connect to outlet API: {e}"
        print(f"TOOL ERROR: {error_msg}")
        return error_msg
    except Exception as e:
        error_msg = f"An unexpected error occurred in outlet_tool: {str(e)}"
        print(f"TOOL ERROR: {error_msg}")
        return error_msg

# Example of how you might test it if run directly (not part of the graph)
if __name__ == "__main__":
    # Correct way to call a @tool decorated function directly for testing
    print(get_outlet_details.invoke({
        "query": "Where is the ZUS Coffee in Mid Valley?",
        "long_term_summary": "User asked about Mid Valley before.",
        "retrieved_context": ["Previous chat: user asked about nearby cafes."]
    }))
    print(get_outlet_details.invoke({
        "query": "List all outlets with dine-in service."
    }))
