"""Web entry point for the moments platform.

The startup defaults live here so the demo can be configured without opening
the package internals. Environment variables still take precedence.
"""

import os


os.environ.setdefault("MYSQL_HOST", "127.0.0.1")
os.environ.setdefault("MYSQL_PORT", "3306")
os.environ.setdefault("MYSQL_USER", "root")
os.environ.setdefault("MYSQL_PASSWORD", "123456")
os.environ.setdefault("MYSQL_DATABASE", "moments_lab")
os.environ.setdefault("WEB_HOST", "127.0.0.1")
os.environ.setdefault("WEB_PORT", "8000")

from moments.web import run_server


if __name__ == "__main__":
    run_server()
