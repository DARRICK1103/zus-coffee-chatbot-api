from typing import List
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# --- LLMs and Embeddings ---
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = FAISS.from_texts([""], embedding_model)

# --- Prompts ---
summary_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content="You are a summarization assistant. Summarize the conversation segment and combine it with the existing summary:\n\nExisting Summary: {existing_summary}"),
    MessagesPlaceholder("messages"),
])
summary_chain = summary_prompt | llm

# --- Main Chat Prompt ---
main_chat_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content="""You are a helpful and friendly AI assistant.
Remember the user's name if told. Be concise and personal.
Current time: Sunday, July 7, 2025. Location: Sibu, Sarawak, Malaysia.

--- Long-Term Summary ---
{long_term_summary}

--- Retrieved Context ---
{retrieved_context}

--- Chat ---
"""),
    MessagesPlaceholder("messages"),
])
main_chat_chain = main_chat_prompt | llm


# --- Constants ---
MAX_RECENT_MESSAGES = 10
MESSAGES_TO_SUMMARIZE_PER_BATCH = 5

# --- Memory Node ---
def manage_memory_node(state: dict) -> dict:
    messages = state["messages"]
    long_term_summary = state.get("long_term_summary", "No prior summary.")

    conversational = [m for m in messages if not isinstance(m, SystemMessage)]

    if len(conversational) > MAX_RECENT_MESSAGES:
        batch = conversational[:MESSAGES_TO_SUMMARIZE_PER_BATCH]
        to_summarize = [m for m in batch if isinstance(m, (HumanMessage, AIMessage))]

        new_summary = summary_chain.invoke({
            "messages": to_summarize,
            "existing_summary": long_term_summary
        }).content.strip()

        if new_summary:
            vectorstore.add_documents([Document(page_content=new_summary)])
            print("DEBUG: Summary added to vectorstore.")

        remaining = conversational[MESSAGES_TO_SUMMARIZE_PER_BATCH:]
        system_messages = [m for m in messages if isinstance(m, SystemMessage)]

        return {
            **state,
            "messages": system_messages + remaining,
            "long_term_summary": new_summary
        }

    return state

# --- Retrieval Node ---
def retrieve_long_term_memory_node(state: dict) -> dict:
    messages = state["messages"]
    last_input = next((m.content for m in reversed(messages) if isinstance(m, HumanMessage)), "")
    docs = []

    if last_input and len(vectorstore.docstore._dict) > 1:
        docs = vectorstore.similarity_search(last_input, k=3)
        print(f"DEBUG: Retrieved {len(docs)} RAG docs.")

    return {
        **state,
        "retrieved_context": [d.page_content for d in docs]
    }
