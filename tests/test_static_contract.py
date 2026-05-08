import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StaticContractTests(unittest.TestCase):
    def read_file(self, relative_path: str) -> str:
        path = ROOT / relative_path
        self.assertTrue(path.exists(), f"{relative_path} should exist")
        return path.read_text(encoding="utf-8")

    def test_requirement_documents_exist(self):
        requirements = self.read_file("docs/requirements.md")
        test_plan = self.read_file("docs/test_plan.md")

        for marker in [
            "R-USER-001",
            "R-FRIEND-002",
            "R-MOMENT-003",
            "R-COMMENT-001",
            "R-ADMIN-005",
        ]:
            self.assertIn(marker, requirements)

        for marker in ["TC-001", "TC-008", "TC-018", "TC-024"]:
            self.assertIn(marker, test_plan)

    def test_schema_contains_required_tables_views_and_triggers(self):
        schema = self.read_file("sql/schema.sql").lower()

        for table in [
            "users",
            "admins",
            "friend_groups",
            "friendships",
            "moments",
            "comments",
            "audit_logs",
        ]:
            self.assertIn(f"create table if not exists {table}", schema)

        self.assertIn("create or replace view v_admin_moments", schema)
        self.assertIn("create or replace view v_friend_moments", schema)
        self.assertIn("create trigger trg_moments_before_update", schema)
        self.assertIn("create trigger trg_comments_after_insert", schema)
        self.assertIn("on delete cascade", schema)
        self.assertIn("check", schema)

    def test_seed_contains_acceptance_accounts(self):
        seed = self.read_file("sql/seed.sql")

        self.assertIn("1001", seed)
        self.assertIn("user1001", seed)
        self.assertIn("9001", seed)
        self.assertIn("admin9001", seed)
        self.assertIn("INSERT INTO moments", seed)
        self.assertIn("INSERT INTO comments", seed)

    def test_cli_program_contract(self):
        app = self.read_file("src/moments_app.py")

        for marker in [
            "def initialize_database",
            "def register_user",
            "def login_user",
            "def add_friend",
            "def delete_friend",
            "def create_moment",
            "def update_moment",
            "def delete_moment",
            "def comment_moment",
            "def login_admin",
            "def admin_delete_moment",
            "def admin_disable_user",
            "def main",
        ]:
            self.assertIn(marker, app)

        for marker in ["commit()", "rollback()", "mysql.connector"]:
            self.assertIn(marker, app)


if __name__ == "__main__":
    unittest.main()
