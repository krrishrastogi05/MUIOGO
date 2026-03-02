from flask import Blueprint, jsonify
import os
from pathlib import Path
from Classes.Base import Config

health_api = Blueprint('HealthRoute', __name__)

@health_api.route("/health", methods=['GET'])
def health():
    """
    Health check endpoint for system readiness verification.
    Returns solver availability, storage status, and app metadata.
    """
    status = {
        "status": "healthy",
        "app": {
            "name": "MUIOGO",
            "version": "5.4",
            "environment": os.getenv('FLASK_ENV', 'production')
        },
        "solvers": check_solvers(),
        "storage": check_storage(),
        "timestamp": __get_timestamp()
    }
    
    # Determine overall health status
    is_healthy = (
        status["storage"]["writable"] and
        status["storage"]["readable"] and
        len(status["solvers"]["available"]) > 0
    )
    
    status["status"] = "healthy" if is_healthy else "degraded"
    http_status = 200 if is_healthy else 503
    
    return jsonify(status), http_status


@health_api.route("/ready", methods=['GET'])
def ready():
    """
    Readiness probe for container orchestration.
    Returns 200 if app can handle requests, 503 otherwise.
    """
    # Check critical dependencies
    storage_ok = os.access(Config.DATA_STORAGE, os.W_OK) and os.access(Config.DATA_STORAGE, os.R_OK)
    solvers_available = len(__get_available_solvers()) > 0
    
    if storage_ok and solvers_available:
        return jsonify({
            "ready": True,
            "message": "Application is ready to accept requests"
        }), 200
    else:
        return jsonify({
            "ready": False,
            "message": "Application is not ready",
            "issues": {
                "storage": storage_ok,
                "solvers": solvers_available
            }
        }), 503


@health_api.route("/version", methods=['GET'])
def version():
    """
    Returns application version information.
    """
    return jsonify({
        "app": "MUIOGO",
        "version": "5.4",
        "api_version": "1.0",
        "python_version": __get_python_version()
    }), 200


def check_solvers():
    """
    Check availability of CLEWS and OG-Core solvers.
    """
    solvers_dir = Path(__file__).parent.parent.parent / 'SOLVERs'
    
    available_solvers = __get_available_solvers()
    
    return {
        "available": available_solvers,
        "count": len(available_solvers),
        "directory": str(solvers_dir),
        "directory_exists": solvers_dir.exists()
    }


def check_storage():
    """
    Check data storage accessibility and permissions.
    """
    storage_path = Path(Config.DATA_STORAGE)
    
    return {
        "path": str(storage_path),
        "exists": storage_path.exists(),
        "readable": os.access(Config.DATA_STORAGE, os.R_OK) if storage_path.exists() else False,
        "writable": os.access(Config.DATA_STORAGE, os.W_OK) if storage_path.exists() else False,
        "free_space_mb": __get_free_space(storage_path) if storage_path.exists() else 0
    }


def __get_available_solvers():
    """
    Scan SOLVERs directory for available solver files.
    """
    solvers_dir = Path(__file__).parent.parent.parent / 'SOLVERs'
    available = []
    
    if solvers_dir.exists():
        # Check for OSeMOSYS model file
        osemosys_model = solvers_dir / 'model.v.5.4.txt'
        if osemosys_model.exists():
            available.append("OSeMOSYS_5.4")
        
        # Future: Add CLEWS and OG-Core solver detection
        # clews_solver = solvers_dir / 'clews_solver.py'
        # if clews_solver.exists():
        #     available.append("CLEWS")
        
        # og_core_solver = solvers_dir / 'og_core_solver.py'
        # if og_core_solver.exists():
        #     available.append("OG-Core")
    
    return available


def __get_free_space(path):
    """
    Get free disk space in MB for the given path.
    """
    try:
        if os.name == 'nt':  # Windows
            import ctypes
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(str(path)), 
                None, 
                None, 
                ctypes.pointer(free_bytes)
            )
            return free_bytes.value / (1024 * 1024)  # Convert to MB
        else:  # Unix/Linux/Mac
            stat = os.statvfs(path)
            return (stat.f_bavail * stat.f_frsize) / (1024 * 1024)  # Convert to MB
    except:
        return 0


def __get_timestamp():
    """
    Get current UTC timestamp.
    """
    from datetime import datetime
    return datetime.utcnow().isoformat() + 'Z'


def __get_python_version():
    """
    Get Python version string.
    """
    import sys
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
