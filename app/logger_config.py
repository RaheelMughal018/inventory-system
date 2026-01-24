import logging
import os

# Logger name
LOG_NAME = os.getenv("APP_LOGGER_NAME", "call_data_importer")

# Create logger
logger = logging.getLogger(LOG_NAME)
logger.setLevel(logging.DEBUG)

# Log format with ISO-like timestamp including milliseconds
LOG_FORMAT = "%(asctime)s.%(msecs)03d - %(filename)s - %(funcName)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

# Formatter
formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Optional file handler (disabled by default in production)
environment = (os.getenv("ENVIRONMENT") or os.getenv("ENV") or "").lower()
is_production = environment in ("prod", "production")
# is_lambda = bool(os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("AWS_EXECUTION_ENV"))

default_log_to_file = "false"
# LOG_TO_FILE = os.getenv("LOG_TO_FILE", default_log_to_file).lower() in ("1", "true", "yes")

# # Determine safe log file path. Lambda can only write to /tmp
# requested_log_file_path = os.getenv("LOG_FILE_PATH")
# if requested_log_file_path:
#     effective_log_file_path = requested_log_file_path
# else:
#     effective_log_file_path = "/tmp/app.log" if is_lambda else "app.log"

# if is_lambda and not effective_log_file_path.startswith("/tmp/"):
#     effective_log_file_path = os.path.join("/tmp", os.path.basename(effective_log_file_path))

# LOG_FILE_PATH = effective_log_file_path

# if LOG_TO_FILE:
#     file_handler = logging.FileHandler(LOG_FILE_PATH)
#     file_handler.setLevel(logging.DEBUG)
#     file_handler.setFormatter(formatter)
#     logger.addHandler(file_handler)

# Avoid duplicate logs when imported in multiple modules
logger.propagate = False