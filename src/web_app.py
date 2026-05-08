import json
import os
import secrets
import sys
from contextlib import closing
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import moments_app as core


WEB_ROOT = ROOT / "web"
WEB_HOST = os.getenv("WEB_HOST", "127.0.0.1")
WEB_PORT = int(os.getenv("WEB_PORT", "8000"))
SESSIONS: dict[str, dict[str, int | str]] = {}


class ApiError(Exception):
    def __init__(self, message: str, status: int = HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.message = message
        self.status = status


def json_default(value):
    return str(value)


def fetch_one(sql: str, params=()):
    with closing(core.connect_database()) as conn, closing(conn.cursor(dictionary=True)) as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone()


def fetch_all(sql: str, params=()):
    with closing(core.connect_database()) as conn, closing(conn.cursor(dictionary=True)) as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def execute_write(sql: str, params=()):
    with closing(core.connect_database()) as conn, closing(conn.cursor()) as cursor:
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount


def require_fields(data: dict, *fields: str) -> None:
    missing = [field for field in fields if data.get(field) in (None, "")]
    if missing:
        raise ApiError("缺少必填字段：" + ", ".join(missing))


def get_session(headers) -> dict[str, int | str]:
    token = headers.get("X-Session-Token", "")
    session = SESSIONS.get(token)
    if not session:
        raise ApiError("请先登录。", HTTPStatus.UNAUTHORIZED)
    return session


def require_role(headers, role: str) -> int:
    session = get_session(headers)
    if session["role"] != role:
        raise ApiError("当前账号无权访问该功能。", HTTPStatus.FORBIDDEN)
    return int(session["id"])


def login(role: str, account_id: int, password: str) -> dict:
    table = "users" if role == "user" else "admins"
    id_column = "user_id" if role == "user" else "admin_id"
    status_clause = " AND status = 'active'" if role == "user" else ""
    row = fetch_one(
        f"""
        SELECT {id_column} AS account_id
        FROM {table}
        WHERE {id_column} = %s AND password_hash = %s{status_clause}
        """,
        (account_id, core.hash_password(password)),
    )
    if not row:
        raise ApiError("账号不存在、密码错误或账号不可用。", HTTPStatus.UNAUTHORIZED)
    token = secrets.token_hex(24)
    SESSIONS[token] = {"role": role, "id": int(row["account_id"])}
    return {"token": token, "role": role, "id": int(row["account_id"])}


def register_user(data: dict) -> dict:
    require_fields(data, "user_id", "password", "name")
    user_id = int(data["user_id"])
    gender = data.get("gender") or "其他"
    age = int(data["age"]) if str(data.get("age", "")).strip() else None
    birth_date = data.get("birth_date") or None
    conn = None
    try:
        conn = core.connect_database()
        conn.start_transaction()
        with closing(conn.cursor()) as cursor:
            cursor.execute(
                """
                INSERT INTO users(user_id, password_hash, name, gender, birth_date, age)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, core.hash_password(data["password"]), data["name"], gender, birth_date, age),
            )
            cursor.execute(
                "INSERT INTO friend_groups(user_id, group_name) VALUES (%s, '默认分组')",
                (user_id,),
            )
        conn.commit()
        return {"message": "注册成功，默认分组已创建。"}
    except Exception as exc:
        if conn:
            conn.rollback()
        raise ApiError(f"注册失败：{exc}")
    finally:
        if conn and conn.is_connected():
            conn.close()


def update_profile(user_id: int, data: dict) -> dict:
    require_fields(data, "name", "gender")
    age = int(data["age"]) if str(data.get("age", "")).strip() else None
    count = execute_write(
        """
        UPDATE users
        SET name = %s, gender = %s, birth_date = %s, age = %s
        WHERE user_id = %s
        """,
        (data["name"], data["gender"], data.get("birth_date") or None, age, user_id),
    )
    return {"message": "个人信息已更新。", "affected": count}


def add_friend(user_id: int, data: dict) -> dict:
    require_fields(data, "friend_user_id")
    friend_id = int(data["friend_user_id"])
    if friend_id == user_id:
        raise ApiError("不能添加自己为好友。")
    group_name = data.get("group_name") or "默认分组"
    conn = None
    try:
        conn = core.connect_database()
        conn.start_transaction()
        with closing(conn.cursor()) as cursor:
            cursor.execute("SELECT 1 FROM users WHERE user_id = %s AND status = 'active'", (friend_id,))
            if not cursor.fetchone():
                raise ApiError("目标用户不存在或不可用。")
            my_group_id = core.get_or_create_group(cursor, user_id, group_name)
            friend_group_id = core.get_or_create_group(cursor, friend_id, "默认分组")
            cursor.execute(
                "INSERT INTO friendships(user_id, friend_user_id, group_id) VALUES (%s, %s, %s)",
                (user_id, friend_id, my_group_id),
            )
            cursor.execute(
                "INSERT INTO friendships(user_id, friend_user_id, group_id) VALUES (%s, %s, %s)",
                (friend_id, user_id, friend_group_id),
            )
        conn.commit()
        return {"message": "好友添加成功。"}
    except ApiError:
        if conn:
            conn.rollback()
        raise
    except Exception as exc:
        if conn:
            conn.rollback()
        raise ApiError(f"添加好友失败：{exc}")
    finally:
        if conn and conn.is_connected():
            conn.close()


def delete_friend(user_id: int, friend_id: int) -> dict:
    count = execute_write(
        """
        DELETE FROM friendships
        WHERE (user_id = %s AND friend_user_id = %s)
           OR (user_id = %s AND friend_user_id = %s)
        """,
        (user_id, friend_id, friend_id, user_id),
    )
    return {"message": "好友关系已删除。", "affected": count}


def create_group(user_id: int, data: dict) -> dict:
    require_fields(data, "group_name")
    count = execute_write(
        "INSERT INTO friend_groups(user_id, group_name) VALUES (%s, %s)",
        (user_id, data["group_name"]),
    )
    return {"message": "分组创建成功。", "affected": count}


def move_friend(user_id: int, data: dict) -> dict:
    require_fields(data, "friend_user_id", "group_name")
    with closing(core.connect_database()) as conn, closing(conn.cursor()) as cursor:
        group_id = core.get_or_create_group(cursor, user_id, data["group_name"])
        cursor.execute(
            "UPDATE friendships SET group_id = %s WHERE user_id = %s AND friend_user_id = %s",
            (group_id, user_id, int(data["friend_user_id"])),
        )
        conn.commit()
        return {"message": "好友分组已更新。", "affected": cursor.rowcount}


def create_moment(user_id: int, data: dict) -> dict:
    require_fields(data, "content")
    count = execute_write(
        "INSERT INTO moments(user_id, content) VALUES (%s, %s)",
        (user_id, data["content"]),
    )
    return {"message": "朋友圈发表成功。", "affected": count}


def update_moment(user_id: int, moment_id: int, data: dict) -> dict:
    require_fields(data, "content")
    count = execute_write(
        "UPDATE moments SET content = %s WHERE moment_id = %s AND user_id = %s",
        (data["content"], moment_id, user_id),
    )
    if count == 0:
        raise ApiError("只能修改自己的朋友圈或朋友圈不存在。", HTTPStatus.NOT_FOUND)
    return {"message": "朋友圈已更新。", "affected": count}


def delete_moment(user_id: int, moment_id: int) -> dict:
    count = execute_write(
        "DELETE FROM moments WHERE moment_id = %s AND user_id = %s",
        (moment_id, user_id),
    )
    if count == 0:
        raise ApiError("只能删除自己的朋友圈或朋友圈不存在。", HTTPStatus.NOT_FOUND)
    return {"message": "朋友圈已删除，相关评论已级联删除。", "affected": count}


def comment_moment(user_id: int, data: dict) -> dict:
    require_fields(data, "moment_id", "content")
    moment_id = int(data["moment_id"])
    row = fetch_one(
        "SELECT 1 FROM v_friend_moments WHERE viewer_id = %s AND moment_id = %s",
        (user_id, moment_id),
    )
    if not row:
        raise ApiError("只能评论好友的朋友圈。", HTTPStatus.FORBIDDEN)
    count = execute_write(
        "INSERT INTO comments(moment_id, commenter_id, content) VALUES (%s, %s, %s)",
        (moment_id, user_id, data["content"]),
    )
    return {"message": "评论成功。", "affected": count}


def admin_update_profile(admin_id: int, data: dict) -> dict:
    require_fields(data, "name")
    count = execute_write(
        "UPDATE admins SET name = %s, phone = %s WHERE admin_id = %s",
        (data["name"], data.get("phone") or None, admin_id),
    )
    return {"message": "管理员信息已更新。", "affected": count}


def admin_delete_moment(admin_id: int, moment_id: int, data: dict) -> dict:
    reason = data.get("reason") or "管理员审核删除"
    conn = None
    try:
        conn = core.connect_database()
        conn.start_transaction()
        with closing(conn.cursor()) as cursor:
            cursor.execute("SELECT user_id FROM moments WHERE moment_id = %s", (moment_id,))
            row = cursor.fetchone()
            if not row:
                raise ApiError("朋友圈不存在。", HTTPStatus.NOT_FOUND)
            cursor.execute(
                """
                INSERT INTO audit_logs(admin_id, action_type, target_user_id, target_moment_id, reason)
                VALUES (%s, 'DELETE_MOMENT', %s, %s, %s)
                """,
                (admin_id, row[0], moment_id, reason),
            )
            cursor.execute("DELETE FROM moments WHERE moment_id = %s", (moment_id,))
        conn.commit()
        return {"message": "朋友圈已审核删除，审计日志已记录。"}
    except ApiError:
        if conn:
            conn.rollback()
        raise
    except Exception as exc:
        if conn:
            conn.rollback()
        raise ApiError(f"删除失败：{exc}")
    finally:
        if conn and conn.is_connected():
            conn.close()


def admin_disable_user(admin_id: int, user_id: int, data: dict) -> dict:
    reason = data.get("reason") or "管理员注销用户"
    conn = None
    try:
        conn = core.connect_database()
        conn.start_transaction()
        with closing(conn.cursor()) as cursor:
            cursor.execute("SELECT 1 FROM users WHERE user_id = %s", (user_id,))
            if not cursor.fetchone():
                raise ApiError("目标用户不存在。", HTTPStatus.NOT_FOUND)
            cursor.execute(
                """
                INSERT INTO audit_logs(admin_id, action_type, target_user_id, reason)
                VALUES (%s, 'DISABLE_USER', %s, %s)
                """,
                (admin_id, user_id, reason),
            )
            cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        conn.commit()
        return {"message": "用户已注销，相关数据已清理。"}
    except ApiError:
        if conn:
            conn.rollback()
        raise
    except Exception as exc:
        if conn:
            conn.rollback()
        raise ApiError(f"注销失败：{exc}")
    finally:
        if conn and conn.is_connected():
            conn.close()


class MomentsHandler(BaseHTTPRequestHandler):
    def send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=json_default).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def serve_file(self, path: str) -> None:
        file_path = WEB_ROOT / ("index.html" if path == "/" else path.lstrip("/"))
        if not file_path.exists() or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = "text/html; charset=utf-8"
        if file_path.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif file_path.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        body = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if not parsed.path.startswith("/api/"):
                self.serve_file(parsed.path)
                return
            self.handle_get(parsed.path, parse_qs(parsed.query))
        except ApiError as exc:
            self.send_json({"error": exc.message}, exc.status)
        except Exception as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self) -> None:
        self.handle_mutation("POST")

    def do_PUT(self) -> None:
        self.handle_mutation("PUT")

    def do_DELETE(self) -> None:
        self.handle_mutation("DELETE")

    def handle_mutation(self, method: str) -> None:
        parsed = urlparse(self.path)
        try:
            data = self.read_json()
            result = self.route_mutation(method, parsed.path, data)
            self.send_json(result)
        except ApiError as exc:
            self.send_json({"error": exc.message}, exc.status)
        except Exception as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def handle_get(self, path: str, query: dict) -> None:
        if path == "/api/users/search":
            user_id = require_role(self.headers, "user")
            keyword = query.get("keyword", [""])[0]
            rows = fetch_all(
                """
                SELECT user_id, name
                FROM users
                WHERE status = 'active'
                  AND user_id <> %s
                  AND (CAST(user_id AS CHAR) = %s OR name LIKE %s)
                ORDER BY user_id
                """,
                (user_id, keyword, f"%{keyword}%"),
            )
            self.send_json({"data": rows})
        elif path == "/api/friends":
            user_id = require_role(self.headers, "user")
            self.send_json({"data": fetch_all(
                """
                SELECT f.friend_user_id, u.name, g.group_name, f.created_at
                FROM friendships f
                JOIN users u ON u.user_id = f.friend_user_id
                JOIN friend_groups g ON g.group_id = f.group_id
                WHERE f.user_id = %s
                ORDER BY g.group_name, f.friend_user_id
                """,
                (user_id,),
            )})
        elif path == "/api/groups":
            user_id = require_role(self.headers, "user")
            self.send_json({"data": fetch_all(
                "SELECT group_id, group_name FROM friend_groups WHERE user_id = %s ORDER BY group_name",
                (user_id,),
            )})
        elif path == "/api/moments/my":
            user_id = require_role(self.headers, "user")
            self.send_json({"data": fetch_all(
                "SELECT moment_id, content, created_at, updated_at FROM moments WHERE user_id = %s ORDER BY updated_at DESC",
                (user_id,),
            )})
        elif path == "/api/moments/friends":
            user_id = require_role(self.headers, "user")
            self.send_json({"data": fetch_all(
                """
                SELECT moment_id, friend_user_id, content, created_at, updated_at, comment_count
                FROM v_friend_moments
                WHERE viewer_id = %s
                ORDER BY updated_at DESC
                """,
                (user_id,),
            )})
        elif path == "/api/comments":
            moment_id = int(query.get("moment_id", ["0"])[0])
            self.send_json({"data": fetch_all(
                "SELECT comment_id, commenter_id, content, created_at FROM comments WHERE moment_id = %s ORDER BY created_at",
                (moment_id,),
            )})
        elif path == "/api/admin/moments":
            require_role(self.headers, "admin")
            self.send_json({"data": fetch_all(
                "SELECT moment_id, author_id, content, created_at, updated_at, comment_count FROM v_admin_moments ORDER BY updated_at DESC"
            )})
        elif path == "/api/admin/audit-logs":
            require_role(self.headers, "admin")
            self.send_json({"data": fetch_all(
                """
                SELECT log_id, admin_id, action_type, target_user_id, target_moment_id, reason, created_at
                FROM audit_logs
                ORDER BY created_at DESC, log_id DESC
                """
            )})
        else:
            raise ApiError("接口不存在。", HTTPStatus.NOT_FOUND)

    def route_mutation(self, method: str, path: str, data: dict) -> dict:
        if method == "POST" and path == "/api/init":
            core.initialize_database()
            return {"message": "数据库初始化完成。"}
        if method == "POST" and path == "/api/register":
            return register_user(data)
        if method == "POST" and path == "/api/login/user":
            require_fields(data, "id", "password")
            return login("user", int(data["id"]), data["password"])
        if method == "POST" and path == "/api/login/admin":
            require_fields(data, "id", "password")
            return login("admin", int(data["id"]), data["password"])
        if method == "PUT" and path == "/api/profile":
            return update_profile(require_role(self.headers, "user"), data)
        if method == "POST" and path == "/api/friends":
            return add_friend(require_role(self.headers, "user"), data)
        if method == "DELETE" and path.startswith("/api/friends/"):
            return delete_friend(require_role(self.headers, "user"), int(path.rsplit("/", 1)[1]))
        if method == "POST" and path == "/api/groups":
            return create_group(require_role(self.headers, "user"), data)
        if method == "PUT" and path == "/api/friends/group":
            return move_friend(require_role(self.headers, "user"), data)
        if method == "POST" and path == "/api/moments":
            return create_moment(require_role(self.headers, "user"), data)
        if method == "PUT" and path.startswith("/api/moments/"):
            return update_moment(require_role(self.headers, "user"), int(path.rsplit("/", 1)[1]), data)
        if method == "DELETE" and path.startswith("/api/moments/"):
            return delete_moment(require_role(self.headers, "user"), int(path.rsplit("/", 1)[1]))
        if method == "POST" and path == "/api/comments":
            return comment_moment(require_role(self.headers, "user"), data)
        if method == "PUT" and path == "/api/admin/profile":
            return admin_update_profile(require_role(self.headers, "admin"), data)
        if method == "DELETE" and path.startswith("/api/admin/moments/"):
            return admin_delete_moment(require_role(self.headers, "admin"), int(path.rsplit("/", 1)[1]), data)
        if method == "DELETE" and path.startswith("/api/admin/users/"):
            return admin_disable_user(require_role(self.headers, "admin"), int(path.rsplit("/", 1)[1]), data)
        raise ApiError("接口不存在。", HTTPStatus.NOT_FOUND)


def run_server() -> None:
    server = ThreadingHTTPServer((WEB_HOST, WEB_PORT), MomentsHandler)
    print(f"Web 前端已启动：http://{WEB_HOST}:{WEB_PORT}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
