# agent/nodes/calculator.py

import re
import json
from langchain_core.messages import AIMessage
from typing import Dict
from agent.memory import llm  # Load shared LLM from memory.py

def calculator_tool_node(state: Dict) -> Dict:
    user_input = ""
    for msg in reversed(state["messages"]):
        if msg.type == "human":
            user_input = msg.content
            break

    try:
        # Let LLM translate natural language to arithmetic expression
        system_prompt = """You are a calculator input parser. Convert the user's request into a valid Python math expression.
        Respond only with the expression, no explanation. Examples:
        "three plus five" => 3 + 5
        "seven times two" => 7 * 2
        "what is 5.5 minus 2" => 5.5 - 2

        If the input cannot be parsed, respond with: INVALID"""


        llm_response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ])

        expr = llm_response.content.strip().strip('"').strip("'")
        # print("Parsed expression:", expr)

        # Validate
        if "INVALID" in expr.upper() or not re.match(r"^[\d\.\+\-\*\/\(\)\s]+$", expr):
            raise ValueError("Could not extract valid expression.")


        result = eval(expr, {"__builtins__": None}, {})
        answer = f"The answer is {result}."

    except Exception as e:
        answer = f"⚠️ Calculator error: {str(e)}"

    return {"messages": [AIMessage(content=answer)]}
