from dataclasses import dataclass
from http import HTTPStatus

from . import db


class ServiceError(Exception):
    def __init__(self, message: str, status: int = HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass(frozen=True)
class Session:
    role: str
    account_id: int


def require_fields(data: dict, *fields: str) -> None:
    missing = [field for field in fields if data.get(field) in (None, "")]
    if missing:
        raise ServiceError("缺少必填字段：" + ", ".join(missing))


def as_optional_int(value):
    if value in (None, ""):
        return None
    return int(value)


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


def register_user(data: dict) -> dict:
    require_fields(data, "user_id", "password", "name")
    user_id = int(data["user_id"])
    age = as_optional_int(data.get("age"))
    with db.transaction() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO users(user_id, password_hash, name, gender, birth_date, age)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    db.hash_password(data["password"]),
                    data["name"],
                    data.get("gender") or "其他",
                    data.get("birth_date") or None,
                    age,
                ),
            )
            cursor.execute(
                "INSERT INTO friend_groups(user_id, group_name) VALUES (%s, '默认分组')",
                (user_id,),
            )
        finally:
            cursor.close()
    return {"message": "注册成功，默认分组已创建。"}


def login_user(account_id: int, password: str) -> Session:
    row = db.fetch_one(
        """
        SELECT user_id
        FROM users
        WHERE user_id = %s AND password_hash = %s AND status = 'active'
        """,
        (account_id, db.hash_password(password)),
    )
    if not row:
        raise ServiceError("账号不存在、密码错误或账号不可用。", HTTPStatus.UNAUTHORIZED)
    return Session("user", int(row["user_id"]))


def login_admin(account_id: int, password: str) -> Session:
    row = db.fetch_one(
        "SELECT admin_id FROM admins WHERE admin_id = %s AND password_hash = %s",
        (account_id, db.hash_password(password)),
    )
    if not row:
        raise ServiceError("管理员不存在或密码错误。", HTTPStatus.UNAUTHORIZED)
    return Session("admin", int(row["admin_id"]))


def update_user_profile(user_id: int, data: dict) -> dict:
    require_fields(data, "name", "gender")
    count = db.execute_write(
        """
        UPDATE users
        SET name = %s, gender = %s, birth_date = %s, age = %s
        WHERE user_id = %s
        """,
        (
            data["name"],
            data["gender"],
            data.get("birth_date") or None,
            as_optional_int(data.get("age")),
            user_id,
        ),
    )
    return {"message": "个人信息已更新。", "affected": count}


def search_users(current_user_id: int, keyword: str) -> list[dict]:
    if keyword.isdigit():
        return db.fetch_all(
            """
            SELECT user_id, name
            FROM users
            WHERE user_id = %s AND user_id <> %s AND status = 'active'
            ORDER BY user_id
            """,
            (int(keyword), current_user_id),
        )
    return db.fetch_all(
        """
        SELECT user_id, name
        FROM users
        WHERE name LIKE %s AND user_id <> %s AND status = 'active'
        ORDER BY user_id
        """,
        (f"%{keyword}%", current_user_id),
    )


def add_friend(user_id: int, data: dict) -> dict:
    require_fields(data, "friend_user_id")
    friend_id = int(data["friend_user_id"])
    if friend_id == user_id:
        raise ServiceError("不能添加自己为好友。")
    with db.transaction() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT 1 FROM users WHERE user_id = %s AND status = 'active'", (friend_id,))
            if not cursor.fetchone():
                raise ServiceError("目标用户不存在或不可用。")
            my_group_id = get_or_create_group(cursor, user_id, data.get("group_name") or "默认分组")
            friend_group_id = get_or_create_group(cursor, friend_id, "默认分组")
            cursor.execute(
                "INSERT INTO friendships(user_id, friend_user_id, group_id) VALUES (%s, %s, %s)",
                (user_id, friend_id, my_group_id),
            )
            cursor.execute(
                "INSERT INTO friendships(user_id, friend_user_id, group_id) VALUES (%s, %s, %s)",
                (friend_id, user_id, friend_group_id),
            )
        finally:
            cursor.close()
    return {"message": "好友添加成功，已建立双向好友关系。"}


def delete_friend(user_id: int, friend_id: int) -> dict:
    count = db.execute_write(
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
    count = db.execute_write(
        "INSERT INTO friend_groups(user_id, group_name) VALUES (%s, %s)",
        (user_id, data["group_name"]),
    )
    return {"message": "分组创建成功。", "affected": count}


def move_friend(user_id: int, data: dict) -> dict:
    require_fields(data, "friend_user_id", "group_name")
    with db.transaction() as conn:
        cursor = conn.cursor()
        try:
            group_id = get_or_create_group(cursor, user_id, data["group_name"])
            cursor.execute(
                "UPDATE friendships SET group_id = %s WHERE user_id = %s AND friend_user_id = %s",
                (group_id, user_id, int(data["friend_user_id"])),
            )
            affected = cursor.rowcount
        finally:
            cursor.close()
    return {"message": "好友分组已更新。", "affected": affected}


def list_friends(user_id: int) -> list[dict]:
    return db.fetch_all(
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


def list_groups(user_id: int) -> list[dict]:
    return db.fetch_all(
        "SELECT group_id, group_name FROM friend_groups WHERE user_id = %s ORDER BY group_name",
        (user_id,),
    )


def create_moment(user_id: int, data: dict) -> dict:
    require_fields(data, "content")
    count = db.execute_write(
        "INSERT INTO moments(user_id, content) VALUES (%s, %s)",
        (user_id, data["content"]),
    )
    return {"message": "朋友圈发表成功。", "affected": count}


def update_moment(user_id: int, moment_id: int, data: dict) -> dict:
    require_fields(data, "content")
    count = db.execute_write(
        "UPDATE moments SET content = %s WHERE moment_id = %s AND user_id = %s",
        (data["content"], moment_id, user_id),
    )
    if count == 0:
        raise ServiceError("只能修改自己的朋友圈或朋友圈不存在。", HTTPStatus.NOT_FOUND)
    return {"message": "朋友圈已更新。", "affected": count}


def delete_moment(user_id: int, moment_id: int) -> dict:
    count = db.execute_write(
        "DELETE FROM moments WHERE moment_id = %s AND user_id = %s",
        (moment_id, user_id),
    )
    if count == 0:
        raise ServiceError("只能删除自己的朋友圈或朋友圈不存在。", HTTPStatus.NOT_FOUND)
    return {"message": "朋友圈已删除，相关评论已级联删除。", "affected": count}


def list_my_moments(user_id: int) -> list[dict]:
    return db.fetch_all(
        """
        SELECT moment_id, content, created_at, updated_at
        FROM moments
        WHERE user_id = %s
        ORDER BY updated_at DESC
        """,
        (user_id,),
    )


def list_friend_moments(user_id: int) -> list[dict]:
    return db.fetch_all(
        """
        SELECT moment_id, friend_user_id, content, created_at, updated_at, comment_count
        FROM v_friend_moments
        WHERE viewer_id = %s
        ORDER BY updated_at DESC
        """,
        (user_id,),
    )


def list_comments(moment_id: int) -> list[dict]:
    return db.fetch_all(
        """
        SELECT comment_id, commenter_id, content, created_at
        FROM comments
        WHERE moment_id = %s
        ORDER BY created_at
        """,
        (moment_id,),
    )


def comment_moment(user_id: int, data: dict) -> dict:
    require_fields(data, "moment_id", "content")
    moment_id = int(data["moment_id"])
    row = db.fetch_one(
        "SELECT 1 FROM v_friend_moments WHERE viewer_id = %s AND moment_id = %s",
        (user_id, moment_id),
    )
    if not row:
        raise ServiceError("只能评论好友的朋友圈。", HTTPStatus.FORBIDDEN)
    count = db.execute_write(
        "INSERT INTO comments(moment_id, commenter_id, content) VALUES (%s, %s, %s)",
        (moment_id, user_id, data["content"]),
    )
    return {"message": "评论成功，朋友圈最后更新时间已由触发器刷新。", "affected": count}


def update_admin_profile(admin_id: int, data: dict) -> dict:
    require_fields(data, "name")
    count = db.execute_write(
        "UPDATE admins SET name = %s, phone = %s WHERE admin_id = %s",
        (data["name"], data.get("phone") or None, admin_id),
    )
    return {"message": "管理员信息已更新。", "affected": count}


def admin_list_moments() -> list[dict]:
    return db.fetch_all(
        """
        SELECT moment_id, author_id, content, created_at, updated_at, comment_count
        FROM v_admin_moments
        ORDER BY updated_at DESC
        """
    )


def admin_delete_moment(admin_id: int, moment_id: int, data: dict) -> dict:
    reason = data.get("reason") or "管理员审核删除"
    with db.transaction() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT user_id FROM moments WHERE moment_id = %s", (moment_id,))
            row = cursor.fetchone()
            if not row:
                raise ServiceError("朋友圈不存在。", HTTPStatus.NOT_FOUND)
            cursor.execute(
                """
                INSERT INTO audit_logs(admin_id, action_type, target_user_id, target_moment_id, reason)
                VALUES (%s, 'DELETE_MOMENT', %s, %s, %s)
                """,
                (admin_id, row[0], moment_id, reason),
            )
            cursor.execute("DELETE FROM moments WHERE moment_id = %s", (moment_id,))
        finally:
            cursor.close()
    return {"message": "朋友圈已审核删除，审计日志已记录。"}


def admin_disable_user(admin_id: int, user_id: int, data: dict) -> dict:
    reason = data.get("reason") or "管理员注销用户"
    with db.transaction() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT 1 FROM users WHERE user_id = %s", (user_id,))
            if not cursor.fetchone():
                raise ServiceError("目标用户不存在。", HTTPStatus.NOT_FOUND)
            cursor.execute(
                """
                INSERT INTO audit_logs(admin_id, action_type, target_user_id, reason)
                VALUES (%s, 'DISABLE_USER', %s, %s)
                """,
                (admin_id, user_id, reason),
            )
            cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        finally:
            cursor.close()
    return {"message": "用户已注销，相关数据已由外键级联清理。"}


def list_audit_logs() -> list[dict]:
    return db.fetch_all(
        """
        SELECT log_id, admin_id, action_type, target_user_id, target_moment_id, reason, created_at
        FROM audit_logs
        ORDER BY created_at DESC, log_id DESC
        """
    )
