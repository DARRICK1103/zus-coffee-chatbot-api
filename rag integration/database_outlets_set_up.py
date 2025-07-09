import os
import json
import sqlite3

def setup_and_ingest_outlet_data():
    """
    Sets up an SQLite database, creates an 'outlets' table with all necessary columns,
    and ingests outlet data from a JSON file.
    """
    # Define paths relative to the script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, "..", "scraped_data", "zus_outlets.json")
    db_dir = os.path.join(script_dir, "..", "database")
    db_path = os.path.join(db_dir, "zus_outlets.db")

    # Create the database directory if it doesn't exist
    os.makedirs(db_dir, exist_ok=True)

    if not os.path.exists(input_file):
        print(f"❌ Error: Input file not found at {input_file}. Please ensure 'scraped_data/zus_outlets.json' exists.")
        return

    print(f"DEBUG: Connecting to SQLite database at {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print("DEBUG: Database connection established.")

    # --- DROP TABLE IF EXISTS (for clean recreation during debugging) ---
    # This ensures you always start with a fresh, correctly-schemed table.
    cursor.execute("DROP TABLE IF EXISTS outlets;")
    print("DEBUG: Dropped existing 'outlets' table (if any).")

    # Define schema and create table - NOW INCLUDING ALL COLUMNS FROM JSON DATA
    create_table_sql = """
    CREATE TABLE outlets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        services TEXT,                   -- Comma-separated string of services
        hours TEXT,                      -- Summary of opening hours (e.g., "Monday–Sunday: 8 am–9:40 pm")
        Maps_link TEXT,           -- URL to Google Maps location
        opening_hours TEXT,              -- JSON string of detailed opening hours dictionary
        full_description TEXT            -- Comprehensive description of the outlet
    );
    """
    print("DEBUG: Creating 'outlets' table with updated schema...")
    cursor.execute(create_table_sql)
    conn.commit()
    print("DEBUG: Table 'outlets' created successfully.")

    print(f"DEBUG: Loading outlet data from {input_file}...")
    with open(input_file, "r", encoding="utf-8") as f:
        outlets_data = json.load(f)
    print(f"DEBUG: Loaded {len(outlets_data)} outlets.")

    if not outlets_data:
        print("⚠️ No outlet data found in the JSON file. Skipping data ingestion.")
        conn.close()
        return

    # Ingest data - NOW INCLUDING ALL NEW COLUMNS
    insert_sql = """
    INSERT INTO outlets (name, address, services, hours, Maps_link, opening_hours, full_description)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """
    print("DEBUG: Ingesting data into 'outlets' table...")
    inserted_count = 0
    for outlet in outlets_data:
        name = outlet.get('name', 'N/A')
        address = outlet.get('address', 'N/A')
        
        # Ensure services is a comma-separated string
        services_list = outlet.get('services', [])
        services_str = ", ".join(services_list) if isinstance(services_list, list) else ""
        
        # Map opening_hours_summary from JSON to 'hours' column in DB
        hours_summary = outlet.get('opening_hours_summary', 'N/A') 
        
        # Get Maps_link
        Maps_link = outlet.get('Maps_link', 'N/A') 

        # Convert detailed opening_hours dictionary to JSON string for DB
        detailed_opening_hours = outlet.get('opening_hours', {})
        detailed_opening_hours_str = json.dumps(detailed_opening_hours)
        
        # Get full_description
        full_description = outlet.get('full_description', 'N/A')

        try:
            cursor.execute(insert_sql, (name, address, services_str, hours_summary, Maps_link, detailed_opening_hours_str, full_description))
            inserted_count += 1
        except sqlite3.IntegrityError as e:
            print(f"WARNING: Could not insert outlet {name} (possibly duplicate): {e}")
        except Exception as e:
            print(f"ERROR: Failed to insert outlet {name}: {e}")
            
    conn.commit()
    print(f"✅ Ingested {inserted_count} records into 'outlets' table.")
    conn.close()
    print("DEBUG: Database connection closed.")

if __name__ == "__main__":
    setup_and_ingest_outlet_data()