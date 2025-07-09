import os
import json
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
import re # Import regex for price extraction

def ingest_product_data_to_vector_store():
    """
    Loads product data from a JSON file, creates embeddings, and saves them
    to a FAISS vector store. Prices are converted to float for better querying.
    """
    input_file = os.path.join("scraped_data", "zus_drinkware_products.json")
    vector_store_path = "product_faiss_index"

    if not os.path.exists(input_file):
        print(f"❌ Error: Input file not found at {input_file}. Please run scrape_products.py first.")
        return

    print("DEBUG: Initializing HuggingFaceEmbeddings model...")
    embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    print("DEBUG: Embedding model initialized.")

    print(f"DEBUG: Loading product data from {input_file}...")
    with open(input_file, "r", encoding="utf-8") as f:
        products_data = json.load(f)
    print(f"DEBUG: Loaded {len(products_data)} products.")

    if not products_data:
        print("⚠️ No product data found in the JSON file. Skipping vector store creation.")
        return

    documents = []
    for product in products_data:
        name = product.get('name', 'N/A')
        raw_price = product.get('price', 'N/A')
        
        # --- Price parsing to float ---
        price_value = None
        if isinstance(raw_price, str):
            # Remove "RM", "from", and any non-numeric characters except dot
            numeric_price_str = re.sub(r'[^\d.]', '', raw_price)
            try:
                price_value = float(numeric_price_str)
            except ValueError:
                price_value = None # Keep as None if conversion fails
        
        variants = product.get('variants', [])
        description = product.get('description', 'N/A')

        content = f"Product Name: {name}\n"
        if price_value is not None:
            content += f"Price: RM{price_value:.2f}\n" # Store formatted price in content
        else:
            content += f"Price: {raw_price}\n" # Keep original if not parsable
        
        if variants:
            content += f"Variants: {', '.join(variants)}\n"
        
        if description and description != "N/A":
            content += f"Description: {description}\n"
        
        # Store numeric price in metadata for filtering
        metadata = {
            "name": name,
            "price_str": raw_price, # Keep original string for display
            "price_float": price_value, # Numeric price for filtering
            "variants": variants
        }
        documents.append(Document(page_content=content.strip(), metadata=metadata))
    
    print(f"DEBUG: Prepared {len(documents)} documents for embedding.")

    print(f"DEBUG: Creating FAISS vector store and saving to {vector_store_path}...")
    db = FAISS.from_documents(documents, embedding_model)
    db.save_local(vector_store_path)
    print(f"✅ FAISS vector store created and saved successfully to {vector_store_path}.")

if __name__ == "__main__":
    ingest_product_data_to_vector_store()
