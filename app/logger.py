import logging
import sys
import json
from datetime import datetime
from contextvars import ContextVar

requestIdContext = ContextVar("request_id", default=None)

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }

        ctxReqId = requestIdContext.get()
        if ctxReqId:
            log_obj["request_id"] = ctxReqId
        
        standard_attributes = {
            'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
            'funcName', 'levelname', 'levelno', 'lineno', 'module',
            'msecs', 'message', 'msg', 'name', 'pathname', 'process',
            'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName'
        }
        
        for key, value in record.__dict__.items():
            if key not in standard_attributes:
                log_obj[key] = value
            
        return json.dumps(log_obj)

def get_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        
    return logger