"""Check if redis is installed"""
import sys
import json
from datetime import datetime

log_path = r"c:\Users\YasserAITLAZIZ\sfd-clm\.cursor\debug.log"

def log_debug(session_id, run_id, hypothesis_id, location, message, data):
    """Log debug information"""
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            entry = {
                "id": f"log_{int(datetime.now().timestamp() * 1000)}",
                "timestamp": int(datetime.now().timestamp() * 1000),
                "location": location,
                "message": message,
                "data": data,
                "sessionId": session_id,
                "runId": run_id,
                "hypothesisId": hypothesis_id
            }
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"Logging error: {e}")

# #region agent log
log_debug("debug-session", "check-1", "A", "check_redis_install.py:20", "Checking Python path", {"python_path": sys.executable, "sys_path": sys.path[:3]})
# #endregion

# #region agent log
log_debug("debug-session", "check-1", "B", "check_redis_install.py:23", "Attempting to import redis", {})
# #endregion

try:
    import redis
    # #region agent log
    log_debug("debug-session", "check-1", "C", "check_redis_install.py:27", "Redis import successful", {"redis_version": getattr(redis, "__version__", "unknown")})
    # #endregion
    print("✓ redis is installed")
    print(f"  Version: {getattr(redis, '__version__', 'unknown')}")
except ImportError as e:
    # #region agent log
    log_debug("debug-session", "check-1", "D", "check_redis_install.py:32", "Redis import failed", {"error": str(e), "error_type": type(e).__name__})
    # #endregion
    print("✗ redis is NOT installed")
    print(f"  Error: {e}")

# #region agent log
log_debug("debug-session", "check-1", "E", "check_redis_install.py:37", "Checking installed packages", {"pip_list_available": True})
# #endregion

try:
    import pkg_resources
    installed = [p.project_name for p in pkg_resources.working_set]
    # #region agent log
    log_debug("debug-session", "check-1", "F", "check_redis_install.py:42", "Installed packages check", {"redis_in_list": "redis" in installed, "total_packages": len(installed)})
    # #endregion
    if "redis" in installed:
        print("✓ redis found in installed packages")
    else:
        print("✗ redis NOT found in installed packages")
        print(f"  Total packages: {len(installed)}")
except Exception as e:
    # #region agent log
    log_debug("debug-session", "check-1", "G", "check_redis_install.py:50", "Package check failed", {"error": str(e)})
    # #endregion
    print(f"Could not check installed packages: {e}")

