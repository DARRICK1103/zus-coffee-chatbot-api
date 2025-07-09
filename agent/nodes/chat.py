from langchain_core.messages import AIMessage
from agent.memory import main_chat_chain  # Make sure it's imported correctly
from typing import Dict

def chat_fallback_node(state: Dict) -> Dict:
    context = {
        "messages": state["messages"],
        "long_term_summary": state.get("long_term_summary", ""),
        "retrieved_context": "\n".join(state.get("retrieved_context", [])) or "No relevant context."
    }

    reply = main_chat_chain.invoke(context)
    return {"messages": [AIMessage(content=reply.content)]}
