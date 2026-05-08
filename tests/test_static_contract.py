import unittest

from helpers import read, read_many


class StaticContractTests(unittest.TestCase):
    def read_file(self, relative_path: str) -> str:
        try:
            return read(relative_path)
        except FileNotFoundError:
            self.fail(f"{relative_path} should exist")

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

    def test_source_is_split_by_responsibility(self):
        for module in [
            "src/moments/config.py",
            "src/moments/db.py",
            "src/moments/sql_runner.py",
            "src/moments/services.py",
            "src/moments/cli.py",
            "src/moments/web.py",
            "src/moments_app.py",
            "src/web_app.py",
        ]:
            self.read_file(module)

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
        app = read_many(
            "src/moments_app.py",
            "src/moments/cli.py",
            "src/moments/services.py",
            "src/moments/sql_runner.py",
        )

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

        infrastructure = read_many(
            "src/moments/db.py",
            "src/moments/sql_runner.py",
        )
        for marker in ["commit()", "rollback()", "mysql.connector"]:
            self.assertIn(marker, infrastructure)

    def test_entry_points_are_thin(self):
        cli_entry = self.read_file("src/moments_app.py")
        web_entry = self.read_file("src/web_app.py")
        self.assertLessEqual(len(cli_entry.splitlines()), 24)
        self.assertLessEqual(len(web_entry.splitlines()), 28)
        for marker in ["run_cli", "run_server"]:
            self.assertIn(marker, cli_entry + web_entry)
        for marker in ["MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE"]:
            self.assertIn(marker, cli_entry + web_entry)

    def test_services_own_business_rules(self):
        services = self.read_file("src/moments/services.py")
        for marker in ["ServiceError", "Session", "db.transaction", "DELETE_MOMENT", "DISABLE_USER"]:
            self.assertIn(marker, services)


if __name__ == "__main__":
    unittest.main()
