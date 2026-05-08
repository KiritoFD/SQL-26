from pathlib import Path

from mysql.connector import Error

from . import config, db


def split_sql_script(script: str):
    delimiter = ";"
    buffer = []
    for raw_line in script.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.upper().startswith("DELIMITER "):
            delimiter = line.split(maxsplit=1)[1]
            continue
        buffer.append(raw_line)
        joined = "\n".join(buffer).strip()
        if joined.endswith(delimiter):
            statement = joined[: -len(delimiter)].strip()
            if statement:
                yield statement
            buffer = []
    tail = "\n".join(buffer).strip()
    if tail:
        yield tail


def execute_sql_file(path: Path, use_database_connection: bool = True) -> None:
    script = path.read_text(encoding="utf-8").replace("moments_lab", config.MYSQL_DATABASE)
    connector = db.connect_database if use_database_connection else db.connect_server
    conn = connector()
    try:
        cursor = conn.cursor()
        try:
            for statement in split_sql_script(script):
                cursor.execute(statement)
            conn.commit()
        finally:
            cursor.close()
    finally:
        conn.close()


def initialize_database() -> str:
    try:
        execute_sql_file(config.ROOT / "sql" / "schema.sql", use_database_connection=False)
        execute_sql_file(config.ROOT / "sql" / "seed.sql", use_database_connection=True)
        return "数据库初始化完成，已创建表、视图、触发器和验收数据。"
    except Error as exc:
        raise RuntimeError(f"数据库初始化失败：{exc}") from exc
