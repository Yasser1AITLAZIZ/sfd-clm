#!/usr/bin/env python3
"""Migration script to add workflow_steps table to SQLite database"""
import sqlite3
import sys
from pathlib import Path
from typing import Optional

# Default database path
DEFAULT_DB_PATH = "backend-mcp/data/sessions.db"


def check_table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """Check if a table exists in the database"""
    cursor = conn.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None


def create_workflow_steps_table(conn: sqlite3.Connection) -> bool:
    """Create the workflow_steps table if it doesn't exist"""
    try:
        # Check if table already exists
        if check_table_exists(conn, "workflow_steps"):
            print("✅ Table 'workflow_steps' already exists")
            return True
        
        print("Creating 'workflow_steps' table...")
        
        # Create workflow_steps table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workflow_steps (
                step_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                workflow_id TEXT NOT NULL,
                step_name TEXT NOT NULL,
                step_order INTEGER NOT NULL,
                status TEXT NOT NULL,
                
                -- Inputs (colonnes séparées pour lisibilité)
                input_record_id TEXT,
                input_user_message TEXT,
                input_documents_count INTEGER,
                input_fields_count INTEGER,
                input_prompt TEXT,
                input_context TEXT,
                
                -- Outputs (colonnes séparées pour lisibilité)
                output_extracted_fields_count INTEGER,
                output_confidence_avg REAL,
                output_status TEXT,
                output_error_message TEXT,
                output_data TEXT,
                
                -- Métadonnées
                started_at TEXT NOT NULL,
                completed_at TEXT,
                processing_time REAL,
                error_details TEXT,
                
                FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes for performance
        print("Creating indexes...")
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_workflow_steps_session 
            ON workflow_steps(session_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_workflow_steps_workflow 
            ON workflow_steps(workflow_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_workflow_steps_step_name 
            ON workflow_steps(step_name)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_workflow_steps_status 
            ON workflow_steps(status)
        """)
        
        conn.commit()
        print("✅ Table 'workflow_steps' created successfully")
        print("✅ Indexes created successfully")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Error creating workflow_steps table: {e}")
        return False


def verify_table_structure(conn: sqlite3.Connection) -> bool:
    """Verify that the workflow_steps table has the correct structure"""
    try:
        cursor = conn.execute("PRAGMA table_info(workflow_steps)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        required_columns = {
            "step_id", "session_id", "workflow_id", "step_name", "step_order", "status",
            "input_record_id", "input_user_message", "input_documents_count", 
            "input_fields_count", "input_prompt", "input_context",
            "output_extracted_fields_count", "output_confidence_avg", "output_status",
            "output_error_message", "output_data",
            "started_at", "completed_at", "processing_time", "error_details"
        }
        
        missing_columns = required_columns - set(columns.keys())
        if missing_columns:
            print(f"❌ Missing columns: {missing_columns}")
            return False
        
        print("✅ Table structure verified")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Error verifying table structure: {e}")
        return False


def migrate_database(db_path: str, backup: bool = True) -> bool:
    """
    Migrate database to add workflow_steps table.
    
    Args:
        db_path: Path to SQLite database file
        backup: Whether to create a backup before migration
        
    Returns:
        True if migration successful, False otherwise
    """
    db_path = Path(db_path)
    
    # Check if database file exists
    if not db_path.exists():
        print(f"⚠️  Database file not found: {db_path}")
        print("   Creating new database with workflow_steps table...")
        # Create parent directory if it doesn't exist
        db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create backup if requested
    if backup and db_path.exists():
        backup_path = db_path.with_suffix(f".backup_{Path(db_path).stat().st_mtime}.db")
        try:
            import shutil
            shutil.copy2(db_path, backup_path)
            print(f"✅ Backup created: {backup_path}")
        except Exception as e:
            print(f"⚠️  Failed to create backup: {e}")
            response = input("Continue without backup? (y/n): ")
            if response.lower() != 'y':
                return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        
        # Check if sessions table exists (required for foreign key)
        if not check_table_exists(conn, "sessions"):
            print("⚠️  Table 'sessions' does not exist. Creating it first...")
            # This will be created by SessionStorage, but we can create a minimal version
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
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
            conn.commit()
            print("✅ Table 'sessions' created")
        
        # Create workflow_steps table
        if not create_workflow_steps_table(conn):
            return False
        
        # Verify table structure
        if not verify_table_structure(conn):
            return False
        
        conn.close()
        print("")
        print("==========================================")
        print("Migration completed successfully!")
        print("==========================================")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate SQLite database to add workflow_steps table"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=DEFAULT_DB_PATH,
        help=f"Path to SQLite database file (default: {DEFAULT_DB_PATH})"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating a backup before migration"
    )
    
    args = parser.parse_args()
    
    # Resolve database path
    db_path = Path(args.db_path)
    if not db_path.is_absolute():
        # Try relative to script directory
        script_dir = Path(__file__).parent
        db_path = script_dir / db_path
        # If still not found, try relative to project root
        if not db_path.exists() and Path("data/sessions.db").exists():
            db_path = Path("data/sessions.db")
    
    print("==========================================")
    print("Workflow Steps Table Migration")
    print("==========================================")
    print(f"Database: {db_path}")
    print("")
    
    success = migrate_database(str(db_path), backup=not args.no_backup)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

