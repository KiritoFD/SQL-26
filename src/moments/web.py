import json
import secrets
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import config, services, sql_runner


SESSIONS: dict[str, services.Session] = {}


def json_default(value):
    return str(value)


def create_session(session: services.Session) -> dict:
    token = secrets.token_hex(24)
    SESSIONS[token] = session
    return {"token": token, "role": session.role, "id": session.account_id}


def get_session(headers) -> services.Session:
    token = headers.get("X-Session-Token", "")
    session = SESSIONS.get(token)
    if not session:
        raise services.ServiceError("请先登录。", HTTPStatus.UNAUTHORIZED)
    return session


def require_role(headers, role: str) -> int:
    session = get_session(headers)
    if session.role != role:
        raise services.ServiceError("当前账号无权访问该功能。", HTTPStatus.FORBIDDEN)
    return session.account_id


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
        file_path = config.WEB_ROOT / ("index.html" if path == "/" else path.lstrip("/"))
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
        except services.ServiceError as exc:
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
            self.send_json(self.route_mutation(method, parsed.path, self.read_json()))
        except services.ServiceError as exc:
            self.send_json({"error": exc.message}, exc.status)
        except Exception as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def handle_get(self, path: str, query: dict) -> None:
        if path == "/api/users/search":
            user_id = require_role(self.headers, "user")
            keyword = query.get("keyword", [""])[0]
            self.send_json({"data": services.search_users(user_id, keyword)})
        elif path == "/api/friends":
            self.send_json({"data": services.list_friends(require_role(self.headers, "user"))})
        elif path == "/api/groups":
            self.send_json({"data": services.list_groups(require_role(self.headers, "user"))})
        elif path == "/api/moments/my":
            self.send_json({"data": services.list_my_moments(require_role(self.headers, "user"))})
        elif path == "/api/moments/friends":
            self.send_json({"data": services.list_friend_moments(require_role(self.headers, "user"))})
        elif path == "/api/comments":
            moment_id = int(query.get("moment_id", ["0"])[0])
            self.send_json({"data": services.list_comments(moment_id)})
        elif path == "/api/admin/moments":
            require_role(self.headers, "admin")
            self.send_json({"data": services.admin_list_moments()})
        elif path == "/api/admin/audit-logs":
            require_role(self.headers, "admin")
            self.send_json({"data": services.list_audit_logs()})
        else:
            raise services.ServiceError("接口不存在。", HTTPStatus.NOT_FOUND)

    def route_mutation(self, method: str, path: str, data: dict) -> dict:
        if method == "POST" and path == "/api/init":
            return {"message": sql_runner.initialize_database()}
        if method == "POST" and path == "/api/register":
            return services.register_user(data)
        if method == "POST" and path == "/api/login/user":
            services.require_fields(data, "id", "password")
            return create_session(services.login_user(int(data["id"]), data["password"]))
        if method == "POST" and path == "/api/login/admin":
            services.require_fields(data, "id", "password")
            return create_session(services.login_admin(int(data["id"]), data["password"]))
        if method == "PUT" and path == "/api/profile":
            return services.update_user_profile(require_role(self.headers, "user"), data)
        if method == "POST" and path == "/api/friends":
            return services.add_friend(require_role(self.headers, "user"), data)
        if method == "DELETE" and path.startswith("/api/friends/"):
            return services.delete_friend(require_role(self.headers, "user"), int(path.rsplit("/", 1)[1]))
        if method == "POST" and path == "/api/groups":
            return services.create_group(require_role(self.headers, "user"), data)
        if method == "PUT" and path == "/api/friends/group":
            return services.move_friend(require_role(self.headers, "user"), data)
        if method == "POST" and path == "/api/moments":
            return services.create_moment(require_role(self.headers, "user"), data)
        if method == "PUT" and path.startswith("/api/moments/"):
            return services.update_moment(require_role(self.headers, "user"), int(path.rsplit("/", 1)[1]), data)
        if method == "DELETE" and path.startswith("/api/moments/"):
            return services.delete_moment(require_role(self.headers, "user"), int(path.rsplit("/", 1)[1]))
        if method == "POST" and path == "/api/comments":
            return services.comment_moment(require_role(self.headers, "user"), data)
        if method == "PUT" and path == "/api/admin/profile":
            return services.update_admin_profile(require_role(self.headers, "admin"), data)
        if method == "DELETE" and path.startswith("/api/admin/moments/"):
            return services.admin_delete_moment(
                require_role(self.headers, "admin"),
                int(path.rsplit("/", 1)[1]),
                data,
            )
        if method == "DELETE" and path.startswith("/api/admin/users/"):
            return services.admin_disable_user(
                require_role(self.headers, "admin"),
                int(path.rsplit("/", 1)[1]),
                data,
            )
        raise services.ServiceError("接口不存在。", HTTPStatus.NOT_FOUND)


def run_server() -> None:
    server = ThreadingHTTPServer((config.WEB_HOST, config.WEB_PORT), MomentsHandler)
    print(f"Web 前端已启动：http://{config.WEB_HOST}:{config.WEB_PORT}")
    server.serve_forever()
