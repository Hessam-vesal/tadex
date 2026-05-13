import logging
import json
from datetime import datetime

logger = logging.getLogger("connection")
logger.setLevel(logging.INFO)

fh = logging.FileHandler("logs/connection.log", encoding="utf-8")
formatter = logging.Formatter("%(message)s")
fh.setFormatter(formatter)
logger.addHandler(fh)

def log_event(service: str, event: str, **kwargs):
    payload = {
        "ts": datetime.utcnow().isoformat(),
        "service": service,
        "event": event,
        **kwargs
    }
    logger.info(json.dumps(payload, ensure_ascii=False))
