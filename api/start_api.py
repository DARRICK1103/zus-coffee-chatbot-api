import os
import json
import re
import traceback
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Query, HTTPException
from typing import List, Dict, Any, Optional

# LangChain imports for RAG and Text2SQL
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.messages import SystemMessage

# For Text2SQL (using create_sql_query_chain and QuerySQLDataBaseTool)
from langchain.chains import create_sql_query_chain
from langchain_community.utilities import SQLDatabase
from langchain_community.tools import QuerySQLDataBaseTool


# --- 1. Load Environment Variables ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables. Please set it in a .env file.")

# --- 2. Initialize FastAPI App ---
app = FastAPI(
    title="ZUS Coffee Data API",
    description="API for retrieving ZUS Coffee product information (RAG) and outlet details (Text2SQL).",
    version="1.0.0",
    openapi_url="/openapi.json"
)

# --- 3. Setup LLM ---
llm = None
try:
    llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=OPENAI_API_KEY) # Using gpt-4o as in your example code
    test_llm_response = llm.invoke("Hello", max_tokens=5)
    print(f"DEBUG: LLM (gpt-4o) initialized and tested successfully. Response start: '{test_llm_response.content}'")
except Exception as e:
    print(f"CRITICAL ERROR: Failed to initialize or connect to OpenAI LLM: {e}")
    print("Please check your OPENAI_API_KEY and network connection.")
    llm = None

# --- 4. Product KB Retrieval Setup (FAISS) ---
PRODUCT_KB_PATH = "product_faiss_index"
product_vectorstore = None
product_retriever = None

if os.path.exists(PRODUCT_KB_PATH):
    print(f"DEBUG: Loading FAISS vector store from {PRODUCT_KB_PATH}...")
    try:
        embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        product_vectorstore = FAISS.load_local(PRODUCT_KB_PATH, embedding_model, allow_dangerous_deserialization=True)
        product_retriever = product_vectorstore.as_retriever(search_kwargs={"k": 10})
        print("DEBUG: Product KB (FAISS) loaded successfully.")
    except Exception as e:
        print(f"❌ Error loading product KB: {e}")
        traceback.print_exc()
        product_vectorstore = None
else:
    print(f"⚠️ Product KB FAISS index not found at {PRODUCT_KB_PATH}. Product retrieval endpoint will not function.")

if product_retriever:
    product_rag_prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content="""You are a helpful assistant for ZUS Coffee products.
        Answer the user's question based only on the provided context. If you cannot find the answer, state that you don't have information on that specific product or detail.
        
        --- Conversation Summary ---
        {long_term_summary}
        
        --- Relevant Past Context ---
        {retrieved_context_str}
        """),
        ("user", "Context: {context}\n\nQuestion: {question}")
    ])

    product_rag_chain = (
        {
            "context": lambda x: x['documents'], 
            "question": RunnablePassthrough(),
            "long_term_summary": lambda x: x.get("long_term_summary", "N/A"),
            "retrieved_context_str": lambda x: "\n".join(x.get("retrieved_context", [])) if x.get("retrieved_context") else "N/A"
        }
        | product_rag_prompt
        | llm
        | StrOutputParser()
    )
else:
    product_rag_chain = None

# --- 5. Outlets Text2SQL Setup (SQLite) ---
script_dir = os.path.dirname(os.path.abspath(__file__))
OUTLETS_DB_PATH = os.path.join(script_dir, "..", "database", "zus_outlets.db") 
db_conn = None
# sql_agent_executor is no longer needed with this approach

db = None
generate_query = None
execute_query = None

if os.path.exists(OUTLETS_DB_PATH):
    print(f"DEBUG: Connecting to SQLite database at {OUTLETS_DB_PATH} for outlets...")
    try:
        db = SQLDatabase.from_uri(f"sqlite:///{OUTLETS_DB_PATH}")
        print("DEBUG: SQLDatabase object created.")

        if llm is None:
            print("CRITICAL ERROR: LLM is not initialized. Cannot create SQL query chain.")
        else:
            generate_query = create_sql_query_chain(llm, db)
            execute_query = QuerySQLDataBaseTool(db=db)
            print("DEBUG: Outlets Text2SQL chain and executor tools initialized successfully.")
    except Exception as e:
        print(f"❌ Error setting up outlets Text2SQL: {e}")
        traceback.print_exc()
else:
    print(f"⚠️ Outlets SQLite database not found at {OUTLETS_DB_PATH}. Outlets Text2SQL endpoint will not function.")

# --- Custom SQL Query Cleaner Function ---
def clean_sql_query(text: str) -> str:
    """
    Clean SQL query by removing code block syntax, various SQL tags, backticks,
    prefixes, and unnecessary whitespace while preserving the core SQL query.

    Args:
        text (str): Raw SQL query text that may contain code blocks, tags, and backticks

    Returns:
        str: Cleaned SQL query
    """
    # Step 1: Remove code block syntax and any SQL-related tags
    # This handles variations like ```sql, ```SQL, ```SQLQuery, etc.
    block_pattern = r"```(?:sql|SQL|SQLQuery|mysql|postgresql)?\s*(.*?)\s*```"
    text = re.sub(block_pattern, r"\1", text, flags=re.DOTALL)

    # Step 2: Handle "SQLQuery:" prefix and similar variations
    # This will match patterns like "SQLQuery:", "SQL Query:", "MySQL:", etc.
    prefix_pattern = r"^(?:SQL\s*Query|SQLQuery|MySQL|PostgreSQL|SQL)\s*:\s*"
    text = re.sub(prefix_pattern, "", text, flags=re.IGNORECASE)

    # Step 3: Extract the first SQL statement if there's random text after it
    # Look for a complete SQL statement ending with semicolon
    sql_statement_pattern = r"(SELECT.*?;)"
    sql_match = re.search(sql_statement_pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if sql_match:
        text = sql_match.group(1)

    # Step 4: Remove backticks around identifiers
    text = re.sub(r'`([^`]*)`', r'\1', text)

    # Step 5: Normalize whitespace
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)

    # Step 6: Preserve newlines for main SQL keywords to maintain readability
    keywords = ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY',
                'LIMIT', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN',
                'OUTER JOIN', 'UNION', 'VALUES', 'INSERT', 'UPDATE', 'DELETE']

    # Case-insensitive replacement for keywords
    pattern = '|'.join(r'\b{}\b'.format(k) for k in keywords)
    text = re.sub(f'({pattern})', r'\n\1', text, flags=re.IGNORECASE)

    # Step 7: Final cleanup
    # Remove leading/trailing whitespace and extra newlines
    text = text.strip()
    text = re.sub(r'\n\s*\n', '\n', text)

    return text

def expand_fuzzy_sql(sql: str) -> str:
    """
    Post-process SQL to support fuzzy address/service matches like 'SS2' vs 'SS 2'.
    """
    # Look for patterns like: WHERE ... LIKE '%SS 2%'
    pattern = re.compile(r"(WHERE\s+[^;]*?)(\"address\"|\"full_description\"|\"services\")\s+LIKE\s+'%(.*?)%'", re.IGNORECASE)
    matches = pattern.findall(sql)
    
    for full_match, column, keyword in matches:
        keyword_no_space = keyword.replace(" ", "")
        fuzzy_clause = f'({column} LIKE \'%{keyword}%\' OR REPLACE({column}, \' \', \'\') LIKE \'%{keyword_no_space}%\')'
        sql = sql.replace(f'{column} LIKE \'%{keyword}%\'', fuzzy_clause)

    return sql


# --- 6. FastAPI Endpoints ---

@app.get("/")
async def read_root():
    return {"message": "Welcome to the ZUS Coffee Data API. Check /docs for API documentation."}

@app.get("/products", response_model=Dict[str, str])
async def get_product_summary(
    query: str = Query(..., description="Natural language query about ZUS Coffee drinkware products."),
    long_term_summary: Optional[str] = Query(None, description="A summary of the ongoing conversation."),
    retrieved_context: Optional[str] = Query("[]", description="Relevant past conversation segments or documents (JSON string of list).")
):
    """
    Retrieves and summarizes information about ZUS Coffee drinkware products
    from the product knowledge base, with optional price filtering and memory context.
    """
    if not product_vectorstore or not product_rag_chain:
        raise HTTPException(status_code=503, detail="Product knowledge base not loaded. Please ensure ingestion script ran successfully.")
    
    retrieved_context_list: List[str] = []
    if retrieved_context:
        try:
            retrieved_context_list = json.loads(retrieved_context)
        except json.JSONDecodeError:
            print(f"WARNING: Could not decode retrieved_context JSON: {retrieved_context}")
            retrieved_context_list = []

    print(f"INFO: Received product query: '{query}'")
    print(f"INFO: Product query memory - Summary: '{long_term_summary[:50]}...', Context: {retrieved_context_list[:1]}")

    min_price, max_price = None, None
    price_below_match = re.search(r'(below|under|less than)\s*(RM)?\s*(\d+(\.\d+)?)', query, re.IGNORECASE)
    price_above_match = re.search(r'(above|over|more than)\s*(RM)?\s*(\d+(\.\d+)?)', query, re.IGNORECASE)
    price_between_match = re.search(r'(between)\s*(RM)?\s*(\d+(\.\d+)?)\s*(and|to)\s*(RM)?\s*(\d+(\.\d+)?)', query, re.IGNORECASE)

    if price_below_match:
        max_price = float(price_below_match.group(3))
    elif price_above_match:
        min_price = float(price_above_match.group(3))
    elif price_between_match:
        min_price = float(price_between_match.group(3))
        max_price = float(price_between_match.group(7))

    try:
        retrieved_docs = product_retriever.invoke(query)
        
        filtered_docs = []
        if min_price is not None or max_price is not None:
            for doc in retrieved_docs:
                doc_price = doc.metadata.get('price_float')
                if doc_price is not None:
                    if (min_price is None or doc_price >= min_price) and \
                       (max_price is None or doc_price <= max_price):
                        filtered_docs.append(doc)
        else:
            filtered_docs = retrieved_docs

        if not filtered_docs:
            return {"summary": "I couldn't find any products matching your criteria, especially with the specified price range. Please try a different query or adjust your budget."}

        response = product_rag_chain.invoke({
            "documents": filtered_docs,
            "question": query,
            "long_term_summary": long_term_summary,
            "retrieved_context": retrieved_context_list
        })
        print(f"INFO: Product RAG response generated.")
        return {"summary": response}
    except Exception as e:
        print(f"❌ Error processing product query: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve product information: {e}")

@app.get("/outlets", response_model=Dict[str, Any])
async def get_outlet_info(
    query: str = Query(..., description="Natural language query about ZUS Coffee outlet locations, hours, or services."),
    long_term_summary: Optional[str] = Query(None, description="A summary of the ongoing conversation."),
    retrieved_context: Optional[str] = Query("[]", description="Relevant past conversation segments or documents (JSON string of list).")
):
    """
    Generates an SQL query from a natural language query, cleans it, executes it against
    the outlets database, and returns the results.
    """
    if generate_query is None or execute_query is None:
        raise HTTPException(status_code=503, detail="Outlets database or SQL chain not ready.")
    
    # You can choose how to incorporate long_term_summary and retrieved_context
    # into the question for the SQL query chain. For simplicity, I'm just
    # using the direct query here, but you could concatenate them.
    # For example:
    # full_question = f"{query}\n\nRelevant past context: {retrieved_context_str}\n\nConversation summary: {long_term_summary}"
    # query_generation_input = {"question": full_question}

    print(f"INFO: Received outlet query: '{query}'")
    print(f"INFO: Outlet query memory - Summary: '{long_term_summary[:50]}...', Context: {retrieved_context[:1]}")

    try:
        # Generate the SQL query
        raw_sql_query = generate_query.invoke({"question": query})
        print(f"DEBUG: Generated raw SQL query: {raw_sql_query}")

        # Clean the generated SQL query
        cleaned_sql_query = clean_sql_query(raw_sql_query)
        print(f"DEBUG: Cleaned SQL query: {cleaned_sql_query}")
  
        fuzzy_sql_query = expand_fuzzy_sql(cleaned_sql_query)
        
        # Execute the cleaned SQL query
        result = execute_query.invoke(fuzzy_sql_query)
        print(f"✅ Query Results: {result}")

        # Langchain's QuerySQLDataBaseTool returns a string representation of the result.
        # You might want to parse this string into a more structured format (e.g., list of dicts)
        # depending on the expected output format for your FastAPI response.
        # For now, we'll return it as a string.

        if not result or "[]" in result: # Check for empty results
             return {
                "query_response": "I couldn't find any information for your query. Please try rephrasing it or searching for a different outlet."
            }

        return {
            "query_response": result,
        }
    except Exception as e:
        print(f"❌ Error processing outlet query: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to retrieve outlet information: {e}")

# --- 7. Run the FastAPI App ---
if __name__ == "__main__":
    print("\n--- Starting FastAPI Application ---")
    print("Access API documentation at: (http://127.0.0.1:8000/docs)")
    uvicorn.run(app, host="0.0.0.0", port=8000)