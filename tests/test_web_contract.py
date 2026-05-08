import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class WebContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entry = read("src/web_app.py")
        cls.backend = read("src/moments/web.py")
        cls.html = read("web/index.html")
        cls.js = read("web/app.js")

    def test_backend_exposes_required_api_routes(self):
        for route in [
            "/api/init",
            "/api/register",
            "/api/login/user",
            "/api/login/admin",
            "/api/profile",
            "/api/users/search",
            "/api/friends",
            "/api/groups",
            "/api/moments/my",
            "/api/moments/friends",
            "/api/comments",
            "/api/admin/profile",
            "/api/admin/moments",
            "/api/admin/audit-logs",
            "/api/admin/users/",
        ]:
            self.assertIn(route, self.backend)

    def test_frontend_contains_user_workflows(self):
        for marker in [
            "用户登录",
            "注册用户",
            "修改个人信息",
            "搜索用户",
            "添加好友",
            "创建分组",
            "移动分组",
            "发表",
            "修改我的朋友圈",
            "删除我的朋友圈",
            "好友朋友圈",
            "发表评论",
        ]:
            self.assertIn(marker, self.html)

    def test_frontend_contains_admin_workflows(self):
        for marker in ["管理员登录", "修改管理员信息", "朋友圈审核", "审核删除", "注销用户", "审计日志"]:
            self.assertIn(marker, self.html)

    def test_frontend_calls_all_critical_endpoints(self):
        for route in [
            "/api/login/user",
            "/api/login/admin",
            "/api/register",
            "/api/friends",
            "/api/moments",
            "/api/moments/friends",
            "/api/admin/moments",
            "/api/admin/audit-logs",
        ]:
            self.assertIn(route, self.js)

    def test_backend_uses_sessions_and_role_checks(self):
        self.assertIn("X-Session-Token", self.backend)
        self.assertIn("require_role", self.backend)
        self.assertIn("HTTPStatus.FORBIDDEN", self.backend)
        self.assertIn("HTTPStatus.UNAUTHORIZED", self.backend)

    def test_web_entry_contains_demo_configuration_defaults(self):
        for marker in ["MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE", "WEB_PORT", "run_server"]:
            self.assertIn(marker, self.entry)


if __name__ == "__main__":
    unittest.main()
