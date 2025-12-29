#!/usr/bin/env python3
"""Script to inspect sessions database"""
import sqlite3
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Default database path
DEFAULT_DB_PATH = "/app/data/sessions.db"


def format_datetime(dt_str: Optional[str]) -> str:
    """Format datetime string for display"""
    if not dt_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return dt_str


def inspect_database(db_path: str):
    """Inspect sessions database"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get table info
        print("=" * 80)
        print("SESSIONS DATABASE INSPECTION")
        print("=" * 80)
        print(f"\nDatabase path: {db_path}")
        print(f"Database exists: {Path(db_path).exists()}")
        
        # List all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\nTables in database: {[row[0] for row in tables]}")
        
        # Check if sessions table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
        if not cursor.fetchone():
            print("\n❌ ERROR: 'sessions' table does not exist!")
            return
        
        # Get table schema
        print("\n" + "=" * 80)
        print("TABLE SCHEMA")
        print("=" * 80)
        cursor.execute("PRAGMA table_info(sessions)")
        columns = cursor.fetchall()
        print("\nColumns:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]}) {'NOT NULL' if col[3] else 'NULL'} {'PRIMARY KEY' if col[5] else ''}")
        
        # Get indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='sessions'")
        indexes = cursor.fetchall()
        if indexes:
            print("\nIndexes:")
            for idx in indexes:
                print(f"  - {idx[0]}")
        
        # Count sessions
        cursor.execute("SELECT COUNT(*) FROM sessions")
        total_sessions = cursor.fetchone()[0]
        print(f"\nTotal sessions: {total_sessions}")
        
        # Count active sessions
        cursor.execute("SELECT COUNT(*) FROM sessions WHERE status = 'active'")
        active_sessions = cursor.fetchone()[0]
        print(f"Active sessions: {active_sessions}")
        
        # Count expired sessions
        now = datetime.utcnow().isoformat()
        cursor.execute("SELECT COUNT(*) FROM sessions WHERE expires_at < ?", (now,))
        expired_sessions = cursor.fetchone()[0]
        print(f"Expired sessions: {expired_sessions}")
        
        # Get recent sessions
        print("\n" + "=" * 80)
        print("RECENT SESSIONS (last 10)")
        print("=" * 80)
        cursor.execute("""
            SELECT session_id, record_id, created_at, updated_at, expires_at, status
            FROM sessions
            ORDER BY created_at DESC
            LIMIT 10
        """)
        sessions = cursor.fetchall()
        
        if not sessions:
            print("\nNo sessions found in database.")
        else:
            print(f"\n{'Session ID':<40} {'Record ID':<25} {'Status':<10} {'Created':<20} {'Expires':<20}")
            print("-" * 120)
            for session in sessions:
                session_id = session['session_id'][:36] + "..." if len(session['session_id']) > 36 else session['session_id']
                record_id = session['record_id'][:23] + "..." if len(session['record_id']) > 23 else session['record_id']
                print(f"{session_id:<40} {record_id:<25} {session['status']:<10} {format_datetime(session['created_at']):<20} {format_datetime(session['expires_at']):<20}")
        
        # Get detailed info for first session
        if sessions:
            print("\n" + "=" * 80)
            print("DETAILED SESSION INFO (first session)")
            print("=" * 80)
            first_session_id = sessions[0]['session_id']
            cursor.execute("""
                SELECT session_id, record_id, created_at, updated_at, expires_at, status,
                       input_data, langgraph_response, interactions_history, processing_metadata
                FROM sessions
                WHERE session_id = ?
            """, (first_session_id,))
            session = cursor.fetchone()
            
            if session:
                print(f"\nSession ID: {session['session_id']}")
                print(f"Record ID: {session['record_id']}")
                print(f"Status: {session['status']}")
                print(f"Created: {format_datetime(session['created_at'])}")
                print(f"Updated: {format_datetime(session['updated_at'])}")
                print(f"Expires: {format_datetime(session['expires_at'])}")
                
                # Parse JSON fields
                try:
                    if session['input_data']:
                        input_data = json.loads(session['input_data'])
                        print(f"\nInput Data (keys): {list(input_data.keys()) if isinstance(input_data, dict) else 'N/A'}")
                except:
                    print(f"\nInput Data: {session['input_data'][:100] if session['input_data'] else 'N/A'}...")
                
                try:
                    if session['langgraph_response']:
                        langgraph_response = json.loads(session['langgraph_response'])
                        print(f"LangGraph Response (keys): {list(langgraph_response.keys()) if isinstance(langgraph_response, dict) else 'N/A'}")
                except:
                    print(f"LangGraph Response: {session['langgraph_response'][:100] if session['langgraph_response'] else 'N/A'}...")
                
                try:
                    if session['interactions_history']:
                        interactions = json.loads(session['interactions_history'])
                        print(f"Interactions History: {len(interactions)} interactions")
                except:
                    print(f"Interactions History: {session['interactions_history'][:100] if session['interactions_history'] else 'N/A'}...")
                
                try:
                    if session['processing_metadata']:
                        metadata = json.loads(session['processing_metadata'])
                        print(f"Processing Metadata (keys): {list(metadata.keys()) if isinstance(metadata, dict) else 'N/A'}")
                except:
                    print(f"Processing Metadata: {session['processing_metadata'][:100] if session['processing_metadata'] else 'N/A'}...")
        
        conn.close()
        print("\n" + "=" * 80)
        print("INSPECTION COMPLETE")
        print("=" * 80)
        
    except sqlite3.Error as e:
        print(f"\n❌ SQLite Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Get database path from command line or use default
    db_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB_PATH
    
    # If running locally, try to find the database
    if not Path(db_path).exists() and Path("data/sessions.db").exists():
        db_path = "data/sessions.db"
    
    inspect_database(db_path)

