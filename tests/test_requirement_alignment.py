import re
import unittest

from helpers import read, read_many


class RequirementAlignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.requirements = read("docs/requirements.md")
        cls.schema = read("sql/schema.sql").lower()
        cls.seed = read("sql/seed.sql")
        cls.cli = read("src/moments/cli.py")
        cls.services = read("src/moments/services.py")
        cls.web = read("src/moments/web.py")
        cls.html = read("src/web/index.html")
        cls.js = read("src/web/app.js")
        cls.all_text = read_many(
            "sql/schema.sql",
            "src/moments/cli.py",
            "src/moments/services.py",
            "src/moments/web.py",
            "src/web/index.html",
            "src/web/app.js",
        )

    def assertCovered(self, requirement_id: str, *markers: str):
        self.assertIn(requirement_id, self.requirements)
        for marker in markers:
            self.assertIn(marker, self.all_text, f"{requirement_id} missing marker: {marker}")

    def test_user_requirements_are_implemented(self):
        self.assertCovered("R-USER-001", "register_user", "默认分组", "db.transaction")
        self.assertCovered("R-USER-002", "login_user", "status = 'active'", "/api/login/user")
        self.assertCovered("R-USER-003", "update_user_profile", "/api/profile", "chk_users_age")

    def test_friend_requirements_are_implemented(self):
        self.assertCovered("R-FRIEND-001", "search_users", "/api/users/search", "SELECT user_id, name")
        self.assertCovered("R-FRIEND-002", "add_friend", "friendships", "不能添加自己")
        self.assertCovered("R-FRIEND-003", "delete_friend", "DELETE FROM friendships")
        self.assertCovered("R-FRIEND-004", "create_group", "move_friend", "uk_friend_groups_user_name")

    def test_moment_and_comment_requirements_are_implemented(self):
        self.assertCovered("R-MOMENT-001", "create_moment", "chk_moments_content_len", "maxlength=\"280\"")
        self.assertCovered("R-MOMENT-002", "update_moment", "trg_moments_before_update")
        self.assertCovered("R-MOMENT-003", "delete_moment", "fk_comments_moment", "ON DELETE CASCADE")
        self.assertCovered("R-MOMENT-004", "v_friend_moments", "comment_count", "loadFriendMoments")
        self.assertCovered("R-COMMENT-001", "comment_moment", "chk_comments_content_len", "trg_comments_after_insert")

    def test_admin_requirements_are_implemented(self):
        self.assertCovered("R-ADMIN-001", "login_admin", "/api/login/admin")
        self.assertCovered("R-ADMIN-002", "update_admin_profile", "/api/admin/profile")
        self.assertCovered("R-ADMIN-003", "v_admin_moments", "admin_list_moments", "author_id")
        self.assertCovered("R-ADMIN-004", "admin_delete_moment", "DELETE_MOMENT", "audit_logs")
        self.assertCovered("R-ADMIN-005", "admin_disable_user", "DISABLE_USER", "DELETE FROM users")

    def test_acceptance_seed_data_is_sufficient(self):
        for account in ["1001", "user1001", "1002", "user1002", "1003", "user1003", "9001", "admin9001"]:
            self.assertIn(account, self.seed)
        self.assertGreaterEqual(len(re.findall(r"INSERT INTO moments", self.seed)), 1)
        self.assertGreaterEqual(len(re.findall(r"INSERT INTO comments", self.seed)), 1)


if __name__ == "__main__":
    unittest.main()
