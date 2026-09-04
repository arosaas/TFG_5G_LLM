def estado_servicio(key: str) -> str:
    """'running', 'stopped', 'error' - with basic health checking via logs"""
    proc = procs[key]
    if proc is None:
        return "stopped"
    rc = proc.poll()
    if rc is not None:
        # Process has terminated
        return "error" if rc != 0 else "stopped"

    # Process is running, do basic health check via logs
    # Look for recent error indicators in the logs
    recent_logs = proc_logs[key][-20:] if proc_logs[key] else []  # Last 20 lines

    # Define error patterns for each service
    error_patterns = {
        "gnb": ["Error", "error", "failed", "Failed", "Segmentation fault", "core dumped"],
        "ue": ["Error", "error", "failed", "Failed", "Segmentation fault", "core dumped"],
        "docker": ["Error", "error", "failed", "Failed", "exited with code", "restarting"]
    }

    # Check for error patterns in recent logs
    patterns = error_patterns.get(key, ["Error", "error", "failed", "Failed"])
    for line in recent_logs:
        line_lower = line.lower()
        for pattern in patterns:
            if pattern.lower() in line_lower:
                return "error"

    # If no errors found in logs, consider it healthy
    return "running"