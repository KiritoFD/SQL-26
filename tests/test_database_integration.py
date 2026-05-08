import os
import unittest


RUN_DB_TESTS = os.getenv("RUN_DB_TESTS") == "1"
os.environ.setdefault("MYSQL_DATABASE", "moments_lab_test")


@unittest.skipUnless(RUN_DB_TESTS, "set RUN_DB_TESTS=1 to run MySQL integration tests")
class DatabaseIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from src.moments import db, services, sql_runner

        cls.db = db
        cls.services = services
        cls.sql_runner = sql_runner
        cls.sql_runner.initialize_database()

    def setUp(self):
        self.sql_runner.initialize_database()

    def scalar(self, sql: str, params=()):
        row = self.db.fetch_one(sql, params)
        if not row:
            return None
        return next(iter(row.values()))

    def test_seed_accounts_can_login_against_real_database(self):
        user = self.services.login_user(1001, "user1001")
        admin = self.services.login_admin(9001, "admin9001")

        self.assertEqual(user.role, "user")
        self.assertEqual(user.account_id, 1001)
        self.assertEqual(admin.role, "admin")
        self.assertEqual(admin.account_id, 9001)

    def test_register_creates_user_and_default_group_in_one_transaction(self):
        self.services.register_user(
            {
                "user_id": 2001,
                "password": "user2001",
                "name": "赵新",
                "gender": "其他",
                "birth_date": "2004-01-01",
                "age": "22",
            }
        )

        group_count = self.scalar(
            "SELECT COUNT(*) AS total FROM friend_groups WHERE user_id = %s AND group_name = '默认分组'",
            (2001,),
        )
        self.assertEqual(group_count, 1)

        with self.assertRaises(Exception):
            self.services.register_user(
                {
                    "user_id": 2001,
                    "password": "dup",
                    "name": "重复用户",
                    "gender": "男",
                }
            )

        user_count = self.scalar("SELECT COUNT(*) AS total FROM users WHERE user_id = %s", (2001,))
        self.assertEqual(user_count, 1)

    def test_friend_add_and_delete_are_bidirectional(self):
        self.services.add_friend(1002, {"friend_user_id": 1003, "group_name": "项目组"})

        forward_count = self.scalar(
            "SELECT COUNT(*) AS total FROM friendships WHERE user_id = 1002 AND friend_user_id = 1003"
        )
        backward_count = self.scalar(
            "SELECT COUNT(*) AS total FROM friendships WHERE user_id = 1003 AND friend_user_id = 1002"
        )
        self.assertEqual(forward_count, 1)
        self.assertEqual(backward_count, 1)

        self.services.delete_friend(1002, 1003)
        total = self.scalar(
            """
            SELECT COUNT(*) AS total
            FROM friendships
            WHERE (user_id = 1002 AND friend_user_id = 1003)
               OR (user_id = 1003 AND friend_user_id = 1002)
            """
        )
        self.assertEqual(total, 0)

    def test_moment_update_comment_trigger_and_delete_cascade(self):
        self.services.create_moment(1002, {"content": "集成测试朋友圈"})
        moment_id = self.scalar(
            "SELECT MAX(moment_id) AS moment_id FROM moments WHERE user_id = 1002 AND content = '集成测试朋友圈'"
        )

        before_update = self.scalar("SELECT updated_at FROM moments WHERE moment_id = %s", (moment_id,))
        self.services.update_moment(1002, moment_id, {"content": "集成测试朋友圈已修改"})
        after_update = self.scalar("SELECT updated_at FROM moments WHERE moment_id = %s", (moment_id,))
        self.assertGreaterEqual(after_update, before_update)

        self.services.comment_moment(1001, {"moment_id": moment_id, "content": "真实评论触发器测试"})
        comment_count = self.scalar("SELECT COUNT(*) AS total FROM comments WHERE moment_id = %s", (moment_id,))
        self.assertEqual(comment_count, 1)

        self.services.delete_moment(1002, moment_id)
        remaining_comments = self.scalar("SELECT COUNT(*) AS total FROM comments WHERE moment_id = %s", (moment_id,))
        self.assertEqual(remaining_comments, 0)

    def test_admin_view_hides_private_profile_and_admin_actions_write_logs(self):
        admin_rows = self.services.admin_list_moments()
        self.assertTrue(admin_rows)
        forbidden = {"name", "gender", "birth_date", "age", "password_hash"}
        self.assertTrue(forbidden.isdisjoint(admin_rows[0].keys()))

        self.services.admin_delete_moment(9001, 2, {"reason": "集成测试审核删除"})
        delete_log_count = self.scalar(
            """
            SELECT COUNT(*) AS total
            FROM audit_logs
            WHERE admin_id = 9001 AND action_type = 'DELETE_MOMENT' AND target_moment_id = 2
            """
        )
        self.assertGreaterEqual(delete_log_count, 1)
        self.assertEqual(self.scalar("SELECT COUNT(*) AS total FROM moments WHERE moment_id = 2"), 0)

        self.services.admin_disable_user(9001, 1003, {"reason": "集成测试注销用户"})
        self.assertEqual(self.scalar("SELECT COUNT(*) AS total FROM users WHERE user_id = 1003"), 0)
        self.assertEqual(self.scalar("SELECT COUNT(*) AS total FROM moments WHERE user_id = 1003"), 0)
        disable_log_count = self.scalar(
            """
            SELECT COUNT(*) AS total
            FROM audit_logs
            WHERE admin_id = 9001 AND action_type = 'DISABLE_USER' AND target_user_id = 1003
            """
        )
        self.assertGreaterEqual(disable_log_count, 1)


if __name__ == "__main__":
    unittest.main()
