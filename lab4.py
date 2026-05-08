import os
import sys
from contextlib import closing

# 优先从项目内依赖目录加载，避免不同 Python 安装之间的包路径冲突。
LOCAL_SITE_PACKAGES = os.path.join(os.path.dirname(__file__), "_vendor")
if os.path.isdir(LOCAL_SITE_PACKAGES):
    sys.path.insert(0, LOCAL_SITE_PACKAGES)

import mysql.connector


HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
PORT = int(os.getenv("MYSQL_PORT", "3306"))
USER = os.getenv("MYSQL_USER", "root")
PASSWORD = os.getenv("MYSQL_PASSWORD", "123456")
DATABASE = "library_lab4"


def print_divider(title: str) -> None:
    print()
    print(f"========== {title} ==========")


def print_rows(cursor) -> None:
    headers = [column[0] for column in cursor.description]
    print("".join(f"{header:<18}" for header in headers))
    for row in cursor.fetchall():
        print("".join(f"{str(value):<18}" for value in row))


def create_database() -> None:
    with closing(
        mysql.connector.connect(
            host=HOST,
            port=PORT,
            user=USER,
            password=PASSWORD,
            charset="utf8mb4",
        )
    ) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS {DATABASE} "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
            )
        conn.commit()
    print(f"任务1+任务2: 已连接 MySQL，并确保数据库存在: {DATABASE}")


def connect_database():
    return mysql.connector.connect(
        host=HOST,
        port=PORT,
        user=USER,
        password=PASSWORD,
        database=DATABASE,
        charset="utf8mb4",
    )


def create_tables(conn) -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS students (
            student_id INT PRIMARY KEY,
            student_name VARCHAR(50) NOT NULL,
            gender VARCHAR(10) NOT NULL,
            age INT NOT NULL,
            major VARCHAR(50) NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS books (
            book_id INT PRIMARY KEY,
            book_name VARCHAR(100) NOT NULL,
            author VARCHAR(50) NOT NULL,
            category VARCHAR(50) NOT NULL,
            stock INT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS borrow_records (
            record_id INT PRIMARY KEY,
            student_id INT NOT NULL,
            book_id INT NOT NULL,
            borrow_date DATE NOT NULL,
            status VARCHAR(20) NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(student_id),
            FOREIGN KEY (book_id) REFERENCES books(book_id)
        )
        """,
    ]
    with closing(conn.cursor()) as cursor:
        for sql in statements:
            cursor.execute(sql)
    conn.commit()
    print("任务2: 3 张数据表创建完成。")


def seed_data(conn) -> None:
    students = [
        (1001, "张明", "男", 20, "计算机科学"),
        (1002, "李华", "女", 19, "软件工程"),
        (1003, "王芳", "女", 21, "信息安全"),
        (1004, "赵强", "男", 22, "人工智能"),
        (1005, "陈雨", "女", 20, "数据科学"),
    ]
    books = [
        (2001, "数据库系统概论", "王珊", "数据库", 6),
        (2002, "Python 程序设计", "董付国", "编程", 5),
        (2003, "计算机网络", "谢希仁", "网络", 4),
        (2004, "操作系统原理", "汤小丹", "系统", 3),
        (2005, "数据结构", "严蔚敏", "基础课", 7),
    ]
    borrow_records = [
        (3001, 1001, 2001, "2026-04-01", "借阅中"),
        (3002, 1002, 2002, "2026-04-03", "已归还"),
        (3003, 1003, 2005, "2026-04-05", "借阅中"),
        (3004, 1004, 2003, "2026-04-06", "已归还"),
        (3005, 1005, 2004, "2026-04-08", "借阅中"),
    ]

    with closing(conn.cursor()) as cursor:
        # 清空旧数据，保证脚本可重复执行。
        cursor.execute("DELETE FROM borrow_records")
        cursor.execute("DELETE FROM books")
        cursor.execute("DELETE FROM students")

        cursor.executemany(
            """
            INSERT INTO students(student_id, student_name, gender, age, major)
            VALUES (%s, %s, %s, %s, %s)
            """,
            students,
        )
        cursor.executemany(
            """
            INSERT INTO books(book_id, book_name, author, category, stock)
            VALUES (%s, %s, %s, %s, %s)
            """,
            books,
        )
        cursor.executemany(
            """
            INSERT INTO borrow_records(record_id, student_id, book_id, borrow_date, status)
            VALUES (%s, %s, %s, %s, %s)
            """,
            borrow_records,
        )
    conn.commit()
    print("任务3: 已为 3 张数据表分别插入 5 条数据。")


def print_query(conn, sql: str) -> None:
    with closing(conn.cursor()) as cursor:
        cursor.execute(sql)
        print_rows(cursor)


def update_student_age(conn, student_id: int, new_age: int) -> None:
    with closing(conn.cursor()) as cursor:
        cursor.execute(
            "UPDATE students SET age = %s WHERE student_id = %s",
            (new_age, student_id),
        )
        print(f"已修改学生学号 {student_id} 的年龄，影响行数: {cursor.rowcount}")
    conn.commit()


def delete_returned_records(conn) -> None:
    with closing(conn.cursor()) as cursor:
        cursor.execute(
            "DELETE FROM borrow_records WHERE status = %s",
            ("已归还",),
        )
        print(f"已删除状态为'已归还'的借阅记录，影响行数: {cursor.rowcount}")
    conn.commit()


def main() -> None:
    try:
        create_database()
        with closing(connect_database()) as conn:
            print(f"成功连接到数据库: {DATABASE}")
            create_tables(conn)
            seed_data(conn)

            print_divider("任务4: 查询学生表中的所有数据")
            print_query(conn, "SELECT * FROM students ORDER BY student_id")

            print_divider("任务5: 多表查询 - 查询学生借书信息")
            print_query(
                conn,
                """
                SELECT br.record_id, s.student_name, b.book_name, br.borrow_date, br.status
                FROM borrow_records br
                JOIN students s ON br.student_id = s.student_id
                JOIN books b ON br.book_id = b.book_id
                ORDER BY br.record_id
                """,
            )

            print_divider("任务6: 修改某位学生年龄后，重新输出学生表")
            update_student_age(conn, 1003, 22)
            print_query(conn, "SELECT * FROM students ORDER BY student_id")

            print_divider("任务7: 删除部分借阅记录后，重新输出借阅表")
            delete_returned_records(conn)
            print_query(conn, "SELECT * FROM borrow_records ORDER BY record_id")
    except mysql.connector.Error as exc:
        print("程序执行失败，请检查 MySQL 服务、账号密码、端口，以及是否安装了 mysql-connector-python。")
        print(f"错误信息: {exc}")


if __name__ == "__main__":
    main()
