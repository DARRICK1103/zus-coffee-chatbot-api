## 🎯 Project Overview

This project provides the intelligent backend for ZUS Coffee's conversational AI assistant. It's designed to understand natural language queries from users and deliver accurate, context-aware responses about ZUS Coffee products and outlet information.

Leveraging cutting-edge AI techniques, the API bridges the gap between unstructured user questions and structured data sources, ensuring a seamless and informative user experience.

---

## ✨ Features

* 🧠 **RAG-based Product Information**: Utilizes **FAISS vector search** for efficient retrieval of answers regarding ZUS Coffee products, ensuring relevant and up-to-date information.
* 🏬 **Text-to-SQL Outlet Search**: Dynamically translates natural language queries into **SQL queries** to fetch precise details about ZUS Coffee outlets, such as locations, operating hours, and amenities.
* 🔄 **Memory-Aware Responses**: Designed to integrate long-term conversation summaries and retrieved context, enabling more personalized and coherent interactions with users.
* ⚡️ **OpenAI GPT-4o Integration**: Combines the high performance and quality of **OpenAI's GPT-4o** for natural language understanding and generation, powered by **HuggingFace embeddings** for vectorization and orchestrated using **LangChain**.
* ✅ **FastAPI Framework**: Built on **FastAPI**, providing a modern, high-performance, and asynchronous-ready API with automatically generated interactive API documentation (Swagger UI) available at the `/docs` endpoint.

---

## 🛠️ Technologies Used

* **Python**: The core programming language for the backend.
* **FastAPI**: Web framework for building robust APIs.
* **LangChain**: Orchestration framework for LLM applications.
* **OpenAI**: Large Language Model provider (GPT-4o).
* **HuggingFace Transformers**: For generating text embeddings.
* **FAISS**: For efficient similarity search in the RAG component.
* **sqlite3**: For interacting with the SQL database (for outlets).

---

## 🚀 Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

* Python 3.9+
* `pip` (Python package installer)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/DARRICK1103/zus-coffee-chatbot-api.git
    ```

2.  **Install Python packages:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Add your OpenAI API Key:**
    Create a `.env` file in the root directory of the project and add your OpenAI API key:
    ```ini
    OPENAI_API_KEY=your_key_here
    ```

### Running Locally

1.  **Start the LangGraph Agent:**
    This runs the core LangChain agent that handles the AI logic.
    ```bash
    python graph.py
    ```

2.  **Start the FastAPI Backend:**
    This will start the API server.
    ```bash
    python api/start_api.py
    ```

### Accessing the API Documentation

Once the FastAPI backend is running, you can access the interactive Swagger UI at:
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

Here, you can explore the available endpoints, test them directly, and understand the API's structure.

---

## 📈 Usage

* **Product Information:** Send natural language queries about ZUS Coffee products (e.g., "What are the ingredients in their Gula Melaka Latte?", "Tell me about the new seasonal drinks.").
* **Outlet Search:** Ask questions about ZUS Coffee outlets (e.g., "Where is the nearest ZUS Coffee?", "What are the opening hours for the outlet in Pavilion Kuala Lumpur?", "Does the Sibu outlet have drive-thru?").
* **Conversational Flow:** The API is designed to work with an external conversational frontend that provides long-term memory/summaries, allowing for more extended and contextual dialogues.

---

---

## 🎬 Demo

Check out a quick demonstration of the ZUS Coffee AI API's conversational capabilities:

<video src="https://github.com/DARRICK1103/zus-coffee-chatbot-api/blob/main/Chatbot_Demo.mp4?raw=true" controls width="700"></video>

---
