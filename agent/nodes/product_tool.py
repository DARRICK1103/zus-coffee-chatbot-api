# agent/nodes/product_tool.py
import json

import requests
from langchain_core.tools import tool
from typing import Dict, Any, List

@tool
def get_product_info(query: str, long_term_summary: str = "", retrieved_context: List[str] = []) -> str:
    """
    Retrieves and summarizes information about ZUS Coffee drinkware products
    from the product knowledge base. Use this tool for questions about products,
    their names, prices, variants, or descriptions, including price-based filters.
    
    Args:
        query (str): The natural language query about ZUS Coffee drinkware products.
        long_term_summary (str): A summary of the ongoing conversation.
        retrieved_context (List[str]): Relevant past conversation segments or documents.
    """
    print(f"TOOL CALL: Calling /products endpoint with query: '{query}'")
    
    params = {
        "query": query,
        "long_term_summary": long_term_summary,
        "retrieved_context": json.dumps(retrieved_context) # Pass list as JSON string
    }

    try:
        resp = requests.get("http://localhost:8000/products", params=params, timeout=10)
        resp.raise_for_status()
        data: Dict[str, Any] = resp.json()

        summary = data.get("summary", "Sorry, I couldn’t find that product info.")
        print(f"TOOL RESPONSE: /products returned: {summary[:100]}...")
        return summary
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to connect to product API: {e}"
        print(f"TOOL ERROR: {error_msg}")
        return error_msg
    except Exception as e:
        error_msg = f"An unexpected error occurred in product_tool: {str(e)}"
        print(f"TOOL ERROR: {error_msg}")
        return error_msg

# Example of how you might test it if run directly (not part of the graph)
if __name__ == "__main__":
    print(get_product_info.invoke({
        "query": "What tumblers do you have?",
        "long_term_summary": "User asked about tumblers before.",
        "retrieved_context": ["Previous chat: user asked about cup sizes."]
    }))
    print(get_product_info.invoke({
        "query": "Show me products below RM 50"
    }))


