#!/usr/bin/env python3
"""Test script to verify database initialization"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.session_storage import SessionStorage
from app.services.workflow_step_storage import WorkflowStepStorage
from app.core.config import settings
import sqlite3

def test_database_initialization():
    """Test that database is properly initialized"""
    print("=" * 80)
    print("TESTING DATABASE INITIALIZATION")
    print("=" * 80)
    
    # Get database path
    db_path = os.getenv("SESSION_DB_PATH", settings.session_db_path)
    print(f"\nDatabase path: {db_path}")
    
    try:
        # Test SessionStorage initialization
        print("\n1. Testing SessionStorage initialization...")
        storage = SessionStorage(
            db_path=db_path,
            default_ttl=86400
        )
        print(f"   ✅ SessionStorage initialized: {storage.db_path}")
        
        # Test WorkflowStepStorage initialization
        print("\n2. Testing WorkflowStepStorage initialization...")
        step_storage = WorkflowStepStorage(db_path=db_path)
        print(f"   ✅ WorkflowStepStorage initialized: {step_storage.db_path}")
        
        # Verify database file exists
        db_file = Path(db_path)
        if not db_file.exists():
            print(f"\n   ⚠️  WARNING: Database file does not exist: {db_path}")
            return False
        
        print(f"   ✅ Database file exists: {db_file.absolute()}")
        
        # Verify tables exist
        print("\n3. Verifying tables...")
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        print(f"   Found tables: {', '.join(tables)}")
        
        # Check sessions table
        if 'sessions' not in tables:
            print("   ❌ ERROR: 'sessions' table not found!")
            return False
        print("   ✅ 'sessions' table exists")
        
        # Check workflow_steps table
        if 'workflow_steps' not in tables:
            print("   ⚠️  WARNING: 'workflow_steps' table not found (will be created on first use)")
        else:
            print("   ✅ 'workflow_steps' table exists")
        
        # Verify table structure
        print("\n4. Verifying table structure...")
        conn = sqlite3.connect(str(db_path))
        
        # Check sessions table columns
        cursor = conn.execute("PRAGMA table_info(sessions)")
        sessions_columns = [row[1] for row in cursor.fetchall()]
        print(f"   Sessions table columns ({len(sessions_columns)}): {', '.join(sessions_columns)}")
        
        required_sessions_columns = ['session_id', 'record_id', 'created_at', 'updated_at', 
                                     'expires_at', 'status', 'input_data', 'langgraph_response',
                                     'interactions_history', 'processing_metadata']
        missing_columns = [col for col in required_sessions_columns if col not in sessions_columns]
        if missing_columns:
            print(f"   ❌ ERROR: Missing columns in sessions table: {', '.join(missing_columns)}")
            conn.close()
            return False
        print("   ✅ All required columns present in 'sessions' table")
        
        # Check workflow_steps table columns (if exists)
        if 'workflow_steps' in tables:
            cursor = conn.execute("PRAGMA table_info(workflow_steps)")
            workflow_steps_columns = [row[1] for row in cursor.fetchall()]
            print(f"   Workflow_steps table columns ({len(workflow_steps_columns)}): {', '.join(workflow_steps_columns[:10])}...")
            
            required_workflow_columns = ['step_id', 'session_id', 'workflow_id', 'step_name', 
                                        'step_order', 'status', 'started_at']
            missing_columns = [col for col in required_workflow_columns if col not in workflow_steps_columns]
            if missing_columns:
                print(f"   ⚠️  WARNING: Missing columns in workflow_steps table: {', '.join(missing_columns)}")
            else:
                print("   ✅ All required columns present in 'workflow_steps' table")
        
        conn.close()
        
        # Verify indexes
        print("\n5. Verifying indexes...")
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='sessions'")
        sessions_indexes = [row[0] for row in cursor.fetchall()]
        print(f"   Sessions indexes: {', '.join(sessions_indexes)}")
        
        if 'workflow_steps' in tables:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='workflow_steps'")
            workflow_indexes = [row[0] for row in cursor.fetchall()]
            print(f"   Workflow_steps indexes: {', '.join(workflow_indexes)}")
        
        conn.close()
        
        print("\n" + "=" * 80)
        print("✅ DATABASE INITIALIZATION TEST PASSED")
        print("=" * 80)
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_database_initialization()
    sys.exit(0 if success else 1)

