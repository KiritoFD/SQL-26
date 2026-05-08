import getpass
import hashlib
import os
import sys
from contextlib import closing
from datetime import datetime
from pathlib import Path

LOCAL_SITE_PACKAGES = Path(__file__).resolve().parents[1] / "_vendor"
if LOCAL_SITE_PACKAGES.is_dir():
    sys.path.insert(0, str(LOCAL_SITE_PACKAGES))

import mysql.connector
from mysql.connector import Error, IntegrityError


ROOT = Path(__file__).resolve().parents[1]
HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
PORT = int(os.getenv("MYSQL_PORT", "3306"))
USER = os.getenv("MYSQL_USER", "root")
PASSWORD = os.getenv("MYSQL_PASSWORD", "123456")
DATABASE = os.getenv("MYSQL_DATABASE", "moments_lab")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def connect_server():
    return mysql.connector.connect(
        host=HOST,
        port=PORT,
        user=USER,
        password=PASSWORD,
        charset="utf8mb4",
    )


def connect_database():
    return mysql.connector.connect(
        host=HOST,
        port=PORT,
        user=USER,
        password=PASSWORD,
        database=DATABASE,
        charset="utf8mb4",
    )


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
    script = path.read_text(encoding="utf-8").replace("moments_lab", DATABASE)
    connector = connect_database if use_database_connection else connect_server
    with closing(connector()) as conn, closing(conn.cursor()) as cursor:
        for statement in split_sql_script(script):
            cursor.execute(statement)
        conn.commit()


def initialize_database() -> None:
    try:
        execute_sql_file(ROOT / "sql" / "schema.sql", use_database_connection=False)
        execute_sql_file(ROOT / "sql" / "seed.sql", use_database_connection=True)
        print("数据库初始化完成，已创建表、视图、触发器和验收数据。")
    except Error as exc:
        print(f"数据库初始化失败：{exc}")


def input_int(prompt: str) -> int | None:
    value = input(prompt).strip()
    if not value.isdigit():
        print("请输入数字。")
        return None
    return int(value)


def input_password(prompt: str = "密码：") -> str:
    try:
        return getpass.getpass(prompt)
    except Exception:
        return input(prompt)


def print_rows(rows, empty_message="没有查询到数据。") -> None:
    if not rows:
        print(empty_message)
        return
    for row in rows:
        print(" | ".join(f"{key}: {value}" for key, value in row.items()))


def register_user() -> None:
    user_id = input_int("用户 id：")
    if user_id is None:
        return
    password = input_password()
    name = input("姓名：").strip()
    gender = input("性别（男/女/其他）：").strip() or "其他"
    birth_date = input("出生日期（YYYY-MM-DD，可空）：").strip() or None
    age_value = input("年龄（可空）：").strip()
    age = int(age_value) if age_value.isdigit() else None

    if not name:
        print("姓名不能为空。")
        return

    conn = None
    try:
        conn = connect_database()
        conn.start_transaction()
        with closing(conn.cursor()) as cursor:
            cursor.execute(
                """
                INSERT INTO users(user_id, password_hash, name, gender, birth_date, age)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, hash_password(password), name, gender, birth_date, age),
            )
            cursor.execute(
                "INSERT INTO friend_groups(user_id, group_name) VALUES (%s, %s)",
                (user_id, "默认分组"),
            )
        conn.commit()
        print("注册成功，已创建默认分组。")
    except IntegrityError as exc:
        if conn:
            conn.rollback()
        print(f"注册失败：用户 id、性别、年龄或分组数据不符合要求。{exc}")
    except Error as exc:
        if conn:
            conn.rollback()
        print(f"注册失败：{exc}")
    finally:
        if conn and conn.is_connected():
            conn.close()


def login_user() -> int | None:
    user_id = input_int("用户 id：")
    if user_id is None:
        return None
    password = input_password()
    try:
        with closing(connect_database()) as conn, closing(conn.cursor(dictionary=True)) as cursor:
            cursor.execute(
                """
                SELECT user_id
                FROM users
                WHERE user_id = %s AND password_hash = %s AND status = 'active'
                """,
                (user_id, hash_password(password)),
            )
            row = cursor.fetchone()
            if row:
                print("用户登录成功。")
                return row["user_id"]
            print("登录失败：账号不存在、密码错误或账号不可用。")
    except Error as exc:
        print(f"登录失败：{exc}")
    return None


def login_admin() -> int | None:
    admin_id = input_int("管理员 id：")
    if admin_id is None:
        return None
    password = input_password()
    try:
        with closing(connect_database()) as conn, closing(conn.cursor(dictionary=True)) as cursor:
            cursor.execute(
                "SELECT admin_id FROM admins WHERE admin_id = %s AND password_hash = %s",
                (admin_id, hash_password(password)),
            )
            row = cursor.fetchone()
            if row:
                print("管理员登录成功。")
                return row["admin_id"]
            print("登录失败：管理员不存在或密码错误。")
    except Error as exc:
        print(f"管理员登录失败：{exc}")
    return None


def update_user_profile(user_id: int) -> None:
    name = input("姓名：").strip()
    gender = input("性别（男/女/其他）：").strip()
    birth_date = input("出生日期（YYYY-MM-DD，可空）：").strip() or None
    age_value = input("年龄（可空）：").strip()
    age = int(age_value) if age_value.isdigit() else None
    try:
        with closing(connect_database()) as conn, closing(conn.cursor()) as cursor:
            cursor.execute(
                """
                UPDATE users
                SET name = %s, gender = %s, birth_date = %s, age = %s
                WHERE user_id = %s
                """,
                (name, gender, birth_date, age, user_id),
            )
            conn.commit()
            print("个人信息已更新。")
    except Error as exc:
        print(f"更新失败：{exc}")


def search_users(current_user_id: int) -> None:
    keyword = input("输入用户 id 或姓名关键字：").strip()
    try:
        with closing(connect_database()) as conn, closing(conn.cursor(dictionary=True)) as cursor:
            if keyword.isdigit():
                cursor.execute(
                    """
                    SELECT user_id, name
                    FROM users
                    WHERE user_id = %s AND user_id <> %s AND status = 'active'
                    """,
                    (int(keyword), current_user_id),
                )
            else:
                cursor.execute(
                    """
                    SELECT user_id, name
                    FROM users
                    WHERE name LIKE %s AND user_id <> %s AND status = 'active'
                    """,
                    (f"%{keyword}%", current_user_id),
                )
            print_rows(cursor.fetchall())
    except Error as exc:
        print(f"搜索失败：{exc}")


def get_or_create_group(cursor, user_id: int, group_name: str) -> int:
    cursor.execute(
        "SELECT group_id FROM friend_groups WHERE user_id = %s AND group_name = %s",
        (user_id, group_name),
    )
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(
        "INSERT INTO friend_groups(user_id, group_name) VALUES (%s, %s)",
        (user_id, group_name),
    )
    return cursor.lastrowid


def add_friend(user_id: int) -> None:
    friend_id = input_int("好友用户 id：")
    if friend_id is None:
        return
    group_name = input("放入我的分组（默认分组）：").strip() or "默认分组"
    if friend_id == user_id:
        print("不能添加自己为好友。")
        return

    conn = None
    try:
        conn = connect_database()
        conn.start_transaction()
        with closing(conn.cursor()) as cursor:
            cursor.execute("SELECT 1 FROM users WHERE user_id = %s AND status = 'active'", (friend_id,))
            if not cursor.fetchone():
                raise ValueError("目标用户不存在或不可用。")
            my_group_id = get_or_create_group(cursor, user_id, group_name)
            friend_group_id = get_or_create_group(cursor, friend_id, "默认分组")
            cursor.execute(
                "INSERT INTO friendships(user_id, friend_user_id, group_id) VALUES (%s, %s, %s)",
                (user_id, friend_id, my_group_id),
            )
            cursor.execute(
                "INSERT INTO friendships(user_id, friend_user_id, group_id) VALUES (%s, %s, %s)",
                (friend_id, user_id, friend_group_id),
            )
        conn.commit()
        print("好友添加成功，已建立双向好友关系。")
    except (Error, ValueError) as exc:
        if conn:
            conn.rollback()
        print(f"添加好友失败：{exc}")
    finally:
        if conn and conn.is_connected():
            conn.close()


def delete_friend(user_id: int) -> None:
    friend_id = input_int("要删除的好友用户 id：")
    if friend_id is None:
        return
    conn = None
    try:
        conn = connect_database()
        conn.start_transaction()
        with closing(conn.cursor()) as cursor:
            cursor.execute(
                """
                DELETE FROM friendships
                WHERE (user_id = %s AND friend_user_id = %s)
                   OR (user_id = %s AND friend_user_id = %s)
                """,
                (user_id, friend_id, friend_id, user_id),
            )
            affected = cursor.rowcount
        conn.commit()
        print(f"删除完成，影响好友关系 {affected} 条。")
    except Error as exc:
        if conn:
            conn.rollback()
        print(f"删除好友失败：{exc}")
    finally:
        if conn and conn.is_connected():
            conn.close()


def create_group(user_id: int) -> None:
    group_name = input("新分组名：").strip()
    if not group_name:
        print("分组名不能为空。")
        return
    try:
        with closing(connect_database()) as conn, closing(conn.cursor()) as cursor:
            cursor.execute(
                "INSERT INTO friend_groups(user_id, group_name) VALUES (%s, %s)",
                (user_id, group_name),
            )
            conn.commit()
            print("分组创建成功。")
    except Error as exc:
        print(f"创建分组失败：{exc}")


def move_friend_group(user_id: int) -> None:
    friend_id = input_int("好友用户 id：")
    if friend_id is None:
        return
    group_name = input("目标分组名：").strip()
    try:
        with closing(connect_database()) as conn, closing(conn.cursor()) as cursor:
            group_id = get_or_create_group(cursor, user_id, group_name)
            cursor.execute(
                """
                UPDATE friendships
                SET group_id = %s
                WHERE user_id = %s AND friend_user_id = %s
                """,
                (group_id, user_id, friend_id),
            )
            conn.commit()
            print("好友分组已更新。")
    except Error as exc:
        print(f"移动分组失败：{exc}")


def list_friends(user_id: int) -> None:
    try:
        with closing(connect_database()) as conn, closing(conn.cursor(dictionary=True)) as cursor:
            cursor.execute(
                """
                SELECT f.friend_user_id, u.name, g.group_name, f.created_at
                FROM friendships f
                JOIN users u ON u.user_id = f.friend_user_id
                JOIN friend_groups g ON g.group_id = f.group_id
                WHERE f.user_id = %s
                ORDER BY g.group_name, f.friend_user_id
                """,
                (user_id,),
            )
            print_rows(cursor.fetchall())
    except Error as exc:
        print(f"查询好友失败：{exc}")


def create_moment(user_id: int) -> None:
    content = input("朋友圈内容（1-280字）：").strip()
    try:
        with closing(connect_database()) as conn, closing(conn.cursor()) as cursor:
            cursor.execute(
                "INSERT INTO moments(user_id, content) VALUES (%s, %s)",
                (user_id, content),
            )
            conn.commit()
            print("朋友圈发表成功。")
    except Error as exc:
        print(f"发表失败：{exc}")


def update_moment(user_id: int) -> None:
    moment_id = input_int("朋友圈 id：")
    if moment_id is None:
        return
    content = input("新内容（1-280字）：").strip()
    try:
        with closing(connect_database()) as conn, closing(conn.cursor()) as cursor:
            cursor.execute(
                "UPDATE moments SET content = %s WHERE moment_id = %s AND user_id = %s",
                (content, moment_id, user_id),
            )
            conn.commit()
            print(f"修改完成，影响 {cursor.rowcount} 条。")
    except Error as exc:
        print(f"修改失败：{exc}")


def delete_moment(user_id: int) -> None:
    moment_id = input_int("朋友圈 id：")
    if moment_id is None:
        return
    try:
        with closing(connect_database()) as conn, closing(conn.cursor()) as cursor:
            cursor.execute(
                "DELETE FROM moments WHERE moment_id = %s AND user_id = %s",
                (moment_id, user_id),
            )
            conn.commit()
            print(f"删除完成，影响 {cursor.rowcount} 条朋友圈，相关评论由外键自动删除。")
    except Error as exc:
        print(f"删除失败：{exc}")


def list_my_moments(user_id: int) -> None:
    try:
        with closing(connect_database()) as conn, closing(conn.cursor(dictionary=True)) as cursor:
            cursor.execute(
                """
                SELECT moment_id, content, created_at, updated_at
                FROM moments
                WHERE user_id = %s
                ORDER BY updated_at DESC
                """,
                (user_id,),
            )
            print_rows(cursor.fetchall())
    except Error as exc:
        print(f"查询失败：{exc}")


def list_friend_moments(user_id: int) -> None:
    try:
        with closing(connect_database()) as conn, closing(conn.cursor(dictionary=True)) as cursor:
            cursor.execute(
                """
                SELECT moment_id, friend_user_id, content, created_at, updated_at, comment_count
                FROM v_friend_moments
                WHERE viewer_id = %s
                ORDER BY updated_at DESC
                """,
                (user_id,),
            )
            print_rows(cursor.fetchall())
    except Error as exc:
        print(f"查询好友朋友圈失败：{exc}")


def list_comments(moment_id: int) -> None:
    try:
        with closing(connect_database()) as conn, closing(conn.cursor(dictionary=True)) as cursor:
            cursor.execute(
                """
                SELECT comment_id, commenter_id, content, created_at
                FROM comments
                WHERE moment_id = %s
                ORDER BY created_at
                """,
                (moment_id,),
            )
            print_rows(cursor.fetchall(), "该朋友圈暂无评论。")
    except Error as exc:
        print(f"查询评论失败：{exc}")


def comment_moment(user_id: int) -> None:
    moment_id = input_int("要评论的朋友圈 id：")
    if moment_id is None:
        return
    content = input("评论内容（1-140字）：").strip()
    try:
        with closing(connect_database()) as conn, closing(conn.cursor()) as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM v_friend_moments
                WHERE viewer_id = %s AND moment_id = %s
                """,
                (user_id, moment_id),
            )
            if not cursor.fetchone():
                print("只能评论好友的朋友圈。")
                return
            cursor.execute(
                "INSERT INTO comments(moment_id, commenter_id, content) VALUES (%s, %s, %s)",
                (moment_id, user_id, content),
            )
            conn.commit()
            print("评论成功，朋友圈最后更新时间已由触发器刷新。")
    except Error as exc:
        print(f"评论失败：{exc}")


def update_admin_profile(admin_id: int) -> None:
    name = input("管理员姓名：").strip()
    phone = input("联系方式：").strip() or None
    try:
        with closing(connect_database()) as conn, closing(conn.cursor()) as cursor:
            cursor.execute(
                "UPDATE admins SET name = %s, phone = %s WHERE admin_id = %s",
                (name, phone, admin_id),
            )
            conn.commit()
            print("管理员信息已更新。")
    except Error as exc:
        print(f"更新失败：{exc}")


def admin_list_moments() -> None:
    try:
        with closing(connect_database()) as conn, closing(conn.cursor(dictionary=True)) as cursor:
            cursor.execute(
                """
                SELECT moment_id, author_id, content, created_at, updated_at, comment_count
                FROM v_admin_moments
                ORDER BY updated_at DESC
                """
            )
            print_rows(cursor.fetchall())
    except Error as exc:
        print(f"查询失败：{exc}")


def admin_delete_moment(admin_id: int) -> None:
    moment_id = input_int("要删除的朋友圈 id：")
    if moment_id is None:
        return
    reason = input("删除原因：").strip() or "管理员审核删除"
    conn = None
    try:
        conn = connect_database()
        conn.start_transaction()
        with closing(conn.cursor()) as cursor:
            cursor.execute("SELECT user_id FROM moments WHERE moment_id = %s", (moment_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError("朋友圈不存在。")
            target_user_id = row[0]
            cursor.execute(
                """
                INSERT INTO audit_logs(admin_id, action_type, target_user_id, target_moment_id, reason)
                VALUES (%s, 'DELETE_MOMENT', %s, %s, %s)
                """,
                (admin_id, target_user_id, moment_id, reason),
            )
            cursor.execute("DELETE FROM moments WHERE moment_id = %s", (moment_id,))
        conn.commit()
        print("朋友圈已删除，审计日志已记录。")
    except (Error, ValueError) as exc:
        if conn:
            conn.rollback()
        print(f"管理员删除朋友圈失败：{exc}")
    finally:
        if conn and conn.is_connected():
            conn.close()


def admin_disable_user(admin_id: int) -> None:
    target_user_id = input_int("要注销的用户 id：")
    if target_user_id is None:
        return
    reason = input("注销原因：").strip() or "管理员注销用户"
    conn = None
    try:
        conn = connect_database()
        conn.start_transaction()
        with closing(conn.cursor()) as cursor:
            cursor.execute("SELECT 1 FROM users WHERE user_id = %s", (target_user_id,))
            if not cursor.fetchone():
                raise ValueError("目标用户不存在。")
            cursor.execute(
                """
                INSERT INTO audit_logs(admin_id, action_type, target_user_id, reason)
                VALUES (%s, 'DISABLE_USER', %s, %s)
                """,
                (admin_id, target_user_id, reason),
            )
            cursor.execute("DELETE FROM users WHERE user_id = %s", (target_user_id,))
        conn.commit()
        print("用户已注销，相关数据已由外键级联清理。")
    except (Error, ValueError) as exc:
        if conn:
            conn.rollback()
        print(f"注销用户失败：{exc}")
    finally:
        if conn and conn.is_connected():
            conn.close()


def list_audit_logs() -> None:
    try:
        with closing(connect_database()) as conn, closing(conn.cursor(dictionary=True)) as cursor:
            cursor.execute(
                """
                SELECT log_id, admin_id, action_type, target_user_id, target_moment_id, reason, created_at
                FROM audit_logs
                ORDER BY created_at DESC, log_id DESC
                """
            )
            print_rows(cursor.fetchall())
    except Error as exc:
        print(f"查询审计日志失败：{exc}")


def show_comments_menu() -> None:
    moment_id = input_int("朋友圈 id：")
    if moment_id is not None:
        list_comments(moment_id)


def user_menu(user_id: int) -> None:
    actions = {
        "1": ("修改个人信息", lambda: update_user_profile(user_id)),
        "2": ("搜索用户", lambda: search_users(user_id)),
        "3": ("添加好友", lambda: add_friend(user_id)),
        "4": ("删除好友", lambda: delete_friend(user_id)),
        "5": ("创建好友分组", lambda: create_group(user_id)),
        "6": ("移动好友分组", lambda: move_friend_group(user_id)),
        "7": ("查看好友列表", lambda: list_friends(user_id)),
        "8": ("发表朋友圈", lambda: create_moment(user_id)),
        "9": ("修改朋友圈", lambda: update_moment(user_id)),
        "10": ("删除朋友圈", lambda: delete_moment(user_id)),
        "11": ("查看我的朋友圈", lambda: list_my_moments(user_id)),
        "12": ("查看好友朋友圈", lambda: list_friend_moments(user_id)),
        "13": ("查看朋友圈评论", show_comments_menu),
        "14": ("评论好友朋友圈", lambda: comment_moment(user_id)),
    }
    menu_loop(f"用户菜单（当前用户 {user_id}）", actions)


def admin_menu(admin_id: int) -> None:
    actions = {
        "1": ("修改管理员信息", lambda: update_admin_profile(admin_id)),
        "2": ("浏览全部朋友圈", admin_list_moments),
        "3": ("删除朋友圈", lambda: admin_delete_moment(admin_id)),
        "4": ("注销用户", lambda: admin_disable_user(admin_id)),
        "5": ("查看审计日志", list_audit_logs),
    }
    menu_loop(f"管理员菜单（当前管理员 {admin_id}）", actions)


def menu_loop(title: str, actions: dict[str, tuple[str, object]]) -> None:
    while True:
        print(f"\n==== {title} ====")
        for key, (label, _) in actions.items():
            print(f"{key}. {label}")
        print("0. 返回")
        choice = input("请选择：").strip()
        if choice == "0":
            return
        action = actions.get(choice)
        if not action:
            print("无效选项。")
            continue
        action[1]()


def main() -> None:
    actions = {
        "1": ("初始化数据库和验收数据", initialize_database),
        "2": ("用户注册", register_user),
        "3": ("用户登录", lambda: (lambda user_id: user_menu(user_id) if user_id else None)(login_user())),
        "4": ("管理员登录", lambda: (lambda admin_id: admin_menu(admin_id) if admin_id else None)(login_admin())),
    }
    print(f"MySQL: {HOST}:{PORT}, database={DATABASE}")
    menu_loop("简易朋友圈平台", actions)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n已退出。{datetime.now():%Y-%m-%d %H:%M:%S}")
