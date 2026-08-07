from datetime import datetime
from sqlalchemy.orm import Session

from models.audit import ProcessLog


def log_process(db: Session, service_id: str, action: str, level: str, message: str) -> ProcessLog:
    """
    Writes a structured audit log entry for Kubernetes/PyroKube operations.
    """
    log_entry = ProcessLog(
        service_id=service_id,
        action=action,
        level=level.upper(),
        message=message,
        timestamp=datetime.utcnow(),
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    
    print(f"[{log_entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] [{level.upper()}] [{service_id}] {message}")
    return log_entry
