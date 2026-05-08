"""Command-line entry point for the moments platform.

Edit the defaults below for a classroom demo, or override them with the same
environment variables before starting the program.
"""

import os


os.environ.setdefault("MYSQL_HOST", "127.0.0.1")
os.environ.setdefault("MYSQL_PORT", "3306")
os.environ.setdefault("MYSQL_USER", "root")
os.environ.setdefault("MYSQL_PASSWORD", "123456")
os.environ.setdefault("MYSQL_DATABASE", "moments_lab")

from moments.cli import run_cli


def main() -> None:
    run_cli()


if __name__ == "__main__":
    main()
