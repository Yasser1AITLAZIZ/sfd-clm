"""
Migration script to convert sessions table from old structure to new refactored structure.

Old structure:
- Single 'data' column with JSON containing everything

New structure:
- Separate columns: input_data, langgraph_response, interactions_history, processing_metadata
- Added 'status' column
"""
import sqlite3
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


def migrate_session_data(old_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert old session data structure to new structure.
    
    Args:
        old_data: Old session data dictionary
        
    Returns:
        Dictionary with new structure fields
    """
    # Extract context from old data
    context = old_data.get("context", {})
    
    # Build input_data from context
    salesforce_data = context.get("salesforce_data", {})
    conversation_history = context.get("conversation_history", [])
    extracted_data = context.get("extracted_data", {})
    old_metadata = context.get("metadata", {})
    
    # Get user_message from first conversation message if available
    user_message = ""
    if conversation_history:
        first_message = conversation_history[0] if isinstance(conversation_history, list) else {}
        if isinstance(first_message, dict) and first_message.get("role") == "user":
            user_message = first_message.get("message", "")
    
    # Build input_data
    input_data = {
        "salesforce_data": salesforce_data,
        "user_message": user_message,
        "context": {
            "documents": salesforce_data.get("documents", []),
            "fields": salesforce_data.get("fields_to_fill", []),
            "session_id": old_data.get("session_id")
        },
        "metadata": {
            "record_id": old_data.get("record_id", ""),
            "record_type": salesforce_data.get("record_type", "Claim"),
            "timestamp": old_data.get("created_at", datetime.utcnow().isoformat())
        },
        "prompt": None,
        "timestamp": old_data.get("created_at", datetime.utcnow().isoformat())
    }
    
    # Build langgraph_response from extracted_data
    langgraph_response = None
    if extracted_data:
        langgraph_response = {
            "extracted_data": extracted_data,
            "confidence_scores": context.get("confidence_scores", {}),
            "quality_score": None,
            "field_mappings": {},
            "processing_time": None,
            "ocr_text_length": None,
            "text_blocks_count": None,
            "timestamp": old_data.get("updated_at", datetime.utcnow().isoformat()),
            "status": "success"
        }
    
    # Build interactions_history from conversation_history
    interactions_history = []
    if conversation_history and isinstance(conversation_history, list):
        for i, msg in enumerate(conversation_history):
            if isinstance(msg, dict):
                interaction = {
                    "interaction_id": f"migrated_{i}_{datetime.utcnow().timestamp()}",
                    "request": {
                        "user_message": msg.get("message", "") if msg.get("role") == "user" else "",
                        "prompt": None,
                        "timestamp": msg.get("timestamp", old_data.get("created_at", datetime.utcnow().isoformat()))
                    },
                    "response": None,
                    "processing_time": None,
                    "status": "success" if msg.get("role") == "assistant" else "pending"
                }
                interactions_history.append(interaction)
    
    # Build processing_metadata
    processing_metadata = {
        "preprocessing_completed": old_metadata.get("preprocessing_completed", False),
        "preprocessing_timestamp": old_data.get("created_at") if old_metadata.get("preprocessing_completed") else None,
        "prompt_built": old_metadata.get("prompt_built", False),
        "prompt_built_timestamp": old_data.get("updated_at") if old_metadata.get("prompt_built") else None,
        "langgraph_processed": old_metadata.get("langgraph_processed", False),
        "langgraph_processed_timestamp": old_data.get("updated_at") if old_metadata.get("langgraph_processed") else None,
        "workflow_id": None,
        "total_processing_time": None,
        "additional_metadata": {}
    }
    
    return {
        "input_data": input_data,
        "langgraph_response": langgraph_response,
        "interactions_history": interactions_history,
        "processing_metadata": processing_metadata,
        "status": "active"  # Default status
    }


def migrate_database(db_path: str, backup: bool = True) -> bool:
    """
    Migrate sessions table from old structure to new structure.
    
    Args:
        db_path: Path to SQLite database file
        backup: Whether to create a backup before migration
        
    Returns:
        True if migration successful, False otherwise
    """
    db_file = Path(db_path)
    
    if not db_file.exists():
        print(f"Error: Database file not found: {db_path}")
        return False
    
    # Create backup if requested
    if backup:
        backup_path = db_path + f".backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        print(f"Creating backup: {backup_path}")
        try:
            import shutil
            shutil.copy2(db_path, backup_path)
            print(f"Backup created successfully")
        except Exception as e:
            print(f"Warning: Failed to create backup: {e}")
            response = input("Continue without backup? (y/n): ")
            if response.lower() != 'y':
                return False
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if old structure exists
        cursor.execute("PRAGMA table_info(sessions)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "data" in columns and "input_data" not in columns:
            print("Old structure detected. Starting migration...")
            
            # Get all sessions with old structure
            cursor.execute("SELECT session_id, record_id, data, created_at, updated_at, expires_at FROM sessions")
            old_sessions = cursor.fetchall()
            
            print(f"Found {len(old_sessions)} sessions to migrate")
            
            # Create new table structure
            print("Creating new table structure...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions_new (
                    session_id TEXT PRIMARY KEY,
                    record_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    input_data TEXT NOT NULL,
                    langgraph_response TEXT,
                    interactions_history TEXT,
                    processing_metadata TEXT
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_expires_at_new ON sessions_new(expires_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_record_id_new ON sessions_new(record_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status_new ON sessions_new(status)")
            
            # Migrate each session
            migrated_count = 0
            error_count = 0
            
            for old_session in old_sessions:
                try:
                    session_id = old_session[0]
                    record_id = old_session[1]
                    old_data_json = old_session[2]
                    created_at = old_session[3]
                    updated_at = old_session[4]
                    expires_at = old_session[5]
                    
                    # Parse old data
                    old_data = json.loads(old_data_json)
                    old_data["session_id"] = session_id
                    old_data["record_id"] = record_id
                    old_data["created_at"] = created_at
                    old_data["updated_at"] = updated_at
                    old_data["expires_at"] = expires_at
                    
                    # Migrate to new structure
                    new_data = migrate_session_data(old_data)
                    
                    # Insert into new table
                    cursor.execute("""
                        INSERT INTO sessions_new (
                            session_id, record_id, created_at, updated_at, expires_at,
                            status, input_data, langgraph_response, interactions_history,
                            processing_metadata
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session_id,
                        record_id,
                        created_at,
                        updated_at,
                        expires_at,
                        new_data["status"],
                        json.dumps(new_data["input_data"]),
                        json.dumps(new_data["langgraph_response"]) if new_data["langgraph_response"] else None,
                        json.dumps(new_data["interactions_history"]),
                        json.dumps(new_data["processing_metadata"])
                    ))
                    
                    migrated_count += 1
                    if migrated_count % 10 == 0:
                        print(f"Migrated {migrated_count} sessions...")
                        
                except Exception as e:
                    error_count += 1
                    print(f"Error migrating session {old_session[0]}: {e}")
                    continue
            
            # Replace old table with new table
            print("Replacing old table with new table...")
            cursor.execute("DROP TABLE IF EXISTS sessions_old")
            cursor.execute("ALTER TABLE sessions RENAME TO sessions_old")
            cursor.execute("ALTER TABLE sessions_new RENAME TO sessions")
            
            # Recreate indexes on new table
            cursor.execute("DROP INDEX IF EXISTS idx_expires_at")
            cursor.execute("DROP INDEX IF EXISTS idx_record_id")
            cursor.execute("DROP INDEX IF EXISTS idx_status")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON sessions(expires_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_record_id ON sessions(record_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON sessions(status)")
            
            conn.commit()
            
            print(f"\nMigration completed!")
            print(f"  - Migrated: {migrated_count} sessions")
            print(f"  - Errors: {error_count} sessions")
            print(f"  - Old table renamed to: sessions_old")
            
            return True
            
        elif "input_data" in columns:
            print("New structure already exists. No migration needed.")
            return True
        else:
            print("Unknown table structure. Cannot migrate.")
            return False
            
    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate sessions table to new structure")
    parser.add_argument(
        "--db-path",
        type=str,
        default="backend-mcp/data/sessions.db",
        help="Path to SQLite database file"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backup before migration"
    )
    
    args = parser.parse_args()
    
    success = migrate_database(args.db_path, backup=not args.no_backup)
    
    sys.exit(0 if success else 1)

