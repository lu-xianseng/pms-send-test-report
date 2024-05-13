import sys
from loguru import logger as log

log.configure(
    handlers=[
        {
            "sink": sys.stderr,
            "format": "{time:YYYY-MM-DD HH:mm:ss} |<lvl>{level:8}| {name}:{line:4} |{message}</>",
        }
    ]
)
log.add(
    "logs.log"
)
