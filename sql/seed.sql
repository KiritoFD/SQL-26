USE moments_lab;

SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE audit_logs;
TRUNCATE TABLE comments;
TRUNCATE TABLE moments;
TRUNCATE TABLE friendships;
TRUNCATE TABLE friend_groups;
TRUNCATE TABLE admins;
TRUNCATE TABLE users;
SET FOREIGN_KEY_CHECKS = 1;

INSERT INTO users (user_id, password_hash, name, gender, birth_date, age)
VALUES
  (1001, SHA2('user1001', 256), '张明', '男', '2004-03-12', 22),
  (1002, SHA2('user1002', 256), '李华', '女', '2005-07-20', 20),
  (1003, SHA2('user1003', 256), '王芳', '女', '2004-11-02', 21);

INSERT INTO admins (admin_id, password_hash, name, phone)
VALUES
  (9001, SHA2('admin9001', 256), '系统管理员', '13800000000');

INSERT INTO friend_groups (user_id, group_name)
VALUES
  (1001, '默认分组'),
  (1001, '同学'),
  (1002, '默认分组'),
  (1002, '朋友'),
  (1003, '默认分组');

INSERT INTO friendships (user_id, friend_user_id, group_id)
VALUES
  (1001, 1002, (SELECT group_id FROM friend_groups WHERE user_id = 1001 AND group_name = '同学')),
  (1002, 1001, (SELECT group_id FROM friend_groups WHERE user_id = 1002 AND group_name = '朋友')),
  (1001, 1003, (SELECT group_id FROM friend_groups WHERE user_id = 1001 AND group_name = '默认分组')),
  (1003, 1001, (SELECT group_id FROM friend_groups WHERE user_id = 1003 AND group_name = '默认分组'));

INSERT INTO moments (moment_id, user_id, content, created_at, updated_at)
VALUES
  (1, 1001, '今天完成了数据库实验的需求分析。', '2026-05-01 09:30:00', '2026-05-01 09:30:00'),
  (2, 1002, 'MySQL 的外键级联删除很适合做朋友圈评论清理。', '2026-05-02 14:20:00', '2026-05-02 14:20:00'),
  (3, 1003, '准备把好友分组也做进系统里。', '2026-05-03 18:10:00', '2026-05-03 18:10:00');

INSERT INTO comments (moment_id, commenter_id, content, created_at)
VALUES
  (2, 1001, '这个设计不错，验收时很好展示。', '2026-05-02 15:00:00'),
  (3, 1001, '分组功能很实用。', '2026-05-03 18:40:00'),
  (1, 1002, '加油，记得补触发器说明。', '2026-05-01 10:00:00');

INSERT INTO audit_logs (admin_id, action_type, target_user_id, target_moment_id, reason)
VALUES
  (9001, 'DELETE_MOMENT', 1002, NULL, '初始化审计日志示例');
