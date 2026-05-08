import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (ROOT / "sql" / "schema.sql").read_text(encoding="utf-8")
SCHEMA_LOWER = SCHEMA.lower()


class SqlContractTests(unittest.TestCase):
    def table_block(self, table_name: str) -> str:
        pattern = rf"create table if not exists {table_name} \((.*?)\) engine=innodb"
        match = re.search(pattern, SCHEMA_LOWER, re.S)
        self.assertIsNotNone(match, f"{table_name} table should be declared")
        return match.group(1)

    def view_block(self, view_name: str) -> str:
        pattern = rf"create or replace view {view_name} as(.*?)(?:create or replace view|delimiter)"
        match = re.search(pattern, SCHEMA_LOWER, re.S)
        self.assertIsNotNone(match, f"{view_name} view should be declared")
        return match.group(1)

    def test_users_table_constraints(self):
        users = self.table_block("users")
        self.assertIn("user_id int primary key", users)
        self.assertIn("password_hash char(64) not null", users)
        self.assertIn("enum", users)
        self.assertIn("chk_users_age", users)
        self.assertIn("between 0 and 150", users)

    def test_friendship_constraints_make_relationships_valid(self):
        friendships = self.table_block("friendships")
        self.assertIn("primary key (user_id, friend_user_id)", friendships)
        self.assertIn("chk_friendships_not_self", friendships)
        self.assertIn("references users(user_id)", friendships)
        self.assertIn("references friend_groups(group_id)", friendships)
        self.assertIn("on delete cascade", friendships)

    def test_moment_and_comment_limits_and_cascade(self):
        moments = self.table_block("moments")
        comments = self.table_block("comments")
        self.assertIn("varchar(280)", moments)
        self.assertIn("char_length(content) between 1 and 280", moments)
        self.assertIn("varchar(140)", comments)
        self.assertIn("char_length(content) between 1 and 140", comments)
        self.assertIn("fk_comments_moment", comments)
        self.assertIn("on delete cascade", comments)

    def test_admin_view_does_not_expose_private_user_profile(self):
        admin_view = self.view_block("v_admin_moments")
        forbidden = ["name", "gender", "birth_date", "age", "password_hash"]
        for column in forbidden:
            self.assertNotIn(column, admin_view)
        for required in ["moment_id", "author_id", "content", "updated_at", "comment_count"]:
            self.assertIn(required, admin_view)

    def test_friend_view_is_based_on_friendship(self):
        friend_view = self.view_block("v_friend_moments")
        self.assertIn("from friendships f", friend_view)
        self.assertIn("join moments m on m.user_id = f.friend_user_id", friend_view)
        self.assertIn("viewer_id", friend_view)

    def test_triggers_cover_update_time_requirements(self):
        self.assertIn("create trigger trg_moments_before_update", SCHEMA_LOWER)
        self.assertIn("set new.updated_at = current_timestamp", SCHEMA_LOWER)
        self.assertIn("create trigger trg_comments_after_insert", SCHEMA_LOWER)
        self.assertIn("update moments", SCHEMA_LOWER)
        self.assertIn("where moment_id = new.moment_id", SCHEMA_LOWER)


if __name__ == "__main__":
    unittest.main()
