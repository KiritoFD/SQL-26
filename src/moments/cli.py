import getpass
from datetime import datetime

from . import config, services, sql_runner


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


def run_action(action, success_prefix: str | None = None) -> None:
    try:
        result = action()
        if isinstance(result, dict):
            print(result.get("message", success_prefix or "操作成功。"))
        elif result is not None:
            print_rows(result)
    except Exception as exc:
        print(f"操作失败：{exc}")


def initialize_database() -> None:
    run_action(lambda: {"message": sql_runner.initialize_database()})


def collect_user_profile() -> dict:
    return {
        "name": input("姓名：").strip(),
        "gender": input("性别（男/女/其他）：").strip() or "其他",
        "birth_date": input("出生日期（YYYY-MM-DD，可空）：").strip(),
        "age": input("年龄（可空）：").strip(),
    }


def register_user() -> None:
    user_id = input_int("用户 id：")
    if user_id is None:
        return
    data = {
        "user_id": user_id,
        "password": input_password(),
        **collect_user_profile(),
    }
    run_action(lambda: services.register_user(data))


def login_user() -> int | None:
    user_id = input_int("用户 id：")
    if user_id is None:
        return None
    try:
        session = services.login_user(user_id, input_password())
        print("用户登录成功。")
        return session.account_id
    except Exception as exc:
        print(f"登录失败：{exc}")
        return None


def login_admin() -> int | None:
    admin_id = input_int("管理员 id：")
    if admin_id is None:
        return None
    try:
        session = services.login_admin(admin_id, input_password())
        print("管理员登录成功。")
        return session.account_id
    except Exception as exc:
        print(f"管理员登录失败：{exc}")
        return None


def update_user_profile(user_id: int) -> None:
    run_action(lambda: services.update_user_profile(user_id, collect_user_profile()))


def search_users(current_user_id: int) -> None:
    keyword = input("输入用户 id 或姓名关键字：").strip()
    run_action(lambda: services.search_users(current_user_id, keyword))


def add_friend(user_id: int) -> None:
    friend_id = input_int("好友用户 id：")
    if friend_id is None:
        return
    data = {
        "friend_user_id": friend_id,
        "group_name": input("放入我的分组（默认分组）：").strip(),
    }
    run_action(lambda: services.add_friend(user_id, data))


def delete_friend(user_id: int) -> None:
    friend_id = input_int("要删除的好友用户 id：")
    if friend_id is not None:
        run_action(lambda: services.delete_friend(user_id, friend_id))


def create_group(user_id: int) -> None:
    run_action(lambda: services.create_group(user_id, {"group_name": input("新分组名：").strip()}))


def move_friend_group(user_id: int) -> None:
    friend_id = input_int("好友用户 id：")
    if friend_id is None:
        return
    data = {
        "friend_user_id": friend_id,
        "group_name": input("目标分组名：").strip(),
    }
    run_action(lambda: services.move_friend(user_id, data))


def list_friends(user_id: int) -> None:
    run_action(lambda: services.list_friends(user_id))


def create_moment(user_id: int) -> None:
    run_action(lambda: services.create_moment(user_id, {"content": input("朋友圈内容（1-280字）：").strip()}))


def update_moment(user_id: int) -> None:
    moment_id = input_int("朋友圈 id：")
    if moment_id is None:
        return
    run_action(lambda: services.update_moment(user_id, moment_id, {"content": input("新内容（1-280字）：").strip()}))


def delete_moment(user_id: int) -> None:
    moment_id = input_int("朋友圈 id：")
    if moment_id is not None:
        run_action(lambda: services.delete_moment(user_id, moment_id))


def list_my_moments(user_id: int) -> None:
    run_action(lambda: services.list_my_moments(user_id))


def list_friend_moments(user_id: int) -> None:
    run_action(lambda: services.list_friend_moments(user_id))


def list_comments(moment_id: int) -> None:
    run_action(lambda: services.list_comments(moment_id))


def comment_moment(user_id: int) -> None:
    moment_id = input_int("要评论的朋友圈 id：")
    if moment_id is None:
        return
    data = {
        "moment_id": moment_id,
        "content": input("评论内容（1-140字）：").strip(),
    }
    run_action(lambda: services.comment_moment(user_id, data))


def update_admin_profile(admin_id: int) -> None:
    data = {
        "name": input("管理员姓名：").strip(),
        "phone": input("联系方式：").strip(),
    }
    run_action(lambda: services.update_admin_profile(admin_id, data))


def admin_list_moments() -> None:
    run_action(services.admin_list_moments)


def admin_delete_moment(admin_id: int) -> None:
    moment_id = input_int("要删除的朋友圈 id：")
    if moment_id is None:
        return
    run_action(lambda: services.admin_delete_moment(admin_id, moment_id, {"reason": input("删除原因：").strip()}))


def admin_disable_user(admin_id: int) -> None:
    target_user_id = input_int("要注销的用户 id：")
    if target_user_id is None:
        return
    run_action(lambda: services.admin_disable_user(admin_id, target_user_id, {"reason": input("注销原因：").strip()}))


def list_audit_logs() -> None:
    run_action(services.list_audit_logs)


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
    print(f"MySQL: {config.MYSQL_HOST}:{config.MYSQL_PORT}, database={config.MYSQL_DATABASE}")
    menu_loop("简易朋友圈平台", actions)


def run_cli() -> None:
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n已退出。{datetime.now():%Y-%m-%d %H:%M:%S}")
