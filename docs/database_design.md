# 数据库设计说明

## 1. 数据库概览

数据库名为 `moments_lab`，采用 InnoDB 引擎和 `utf8mb4` 字符集，支持中文朋友圈内容、评论和姓名。

核心实体包括普通用户、管理员、好友分组、好友关系、朋友圈、评论和审计日志。

## 2. 表结构说明

### users

保存普通用户账号与个人资料。

关键字段：

- `user_id`：普通用户 id，主键。
- `password_hash`：密码哈希。
- `name`、`gender`、`birth_date`、`age`：个人基本信息。
- `status`：账号状态，当前保留 `active` 和 `disabled`。

约束：

- `age` 必须为空或在 0 到 150 之间。
- `gender` 使用枚举限制为男、女、其他。

### admins

保存管理员账号和基本信息。

关键字段：

- `admin_id`：管理员 id，主键。
- `password_hash`：密码哈希。
- `name`、`phone`：管理员基本信息。

### friend_groups

保存每个用户自己的好友分组。

约束：

- `user_id` 外键关联 `users`。
- 同一用户下 `group_name` 唯一。
- 用户删除后，分组自动删除。

### friendships

保存好友关系。系统在添加好友时插入两条记录，实现双向好友。

约束：

- `(user_id, friend_user_id)` 为联合主键。
- `user_id <> friend_user_id` 防止添加自己。
- 删除用户或分组时，相关好友关系级联删除。

### moments

保存朋友圈。

约束：

- `content` 字数为 1 到 280。
- 删除用户时，该用户朋友圈级联删除。
- `updated_at` 表示最后更新时间。

### comments

保存朋友圈评论。

约束：

- `content` 字数为 1 到 140。
- 删除朋友圈时，相关评论级联删除。
- 删除评论者用户时，其评论级联删除。

### audit_logs

保存管理员审核与注销操作日志。

关键字段：

- `admin_id`：执行操作的管理员。
- `action_type`：`DELETE_MOMENT` 或 `DISABLE_USER`。
- `target_user_id`、`target_moment_id`：操作对象。
- `reason`：操作原因。

## 3. 视图设计

### v_admin_moments

管理员审核朋友圈使用。该视图只暴露：

- 朋友圈 id
- 作者 id
- 内容
- 创建时间
- 最后更新时间
- 评论数量

该视图不包含用户姓名、性别、出生日期、年龄，满足管理员不可浏览用户个人基本信息的要求。

### v_friend_moments

普通用户查看好友朋友圈使用。该视图基于 `friendships` 和 `moments` 连接，只返回当前查看者好友的朋友圈。

## 4. 触发器设计

### trg_moments_before_update

当朋友圈内容发生修改时，自动刷新 `updated_at`。

### trg_comments_after_insert

当新增评论后，自动刷新对应朋友圈的 `updated_at`，体现朋友圈最后互动时间。

## 5. 事务设计

后续应用代码需要在以下场景中显式使用事务：

- 注册用户：插入 `users` 与默认 `friend_groups`。
- 添加好友：插入双方 `friendships`。
- 删除好友：删除双方 `friendships`。
- 管理员删除朋友圈：写入 `audit_logs` 并删除 `moments`。
- 管理员注销用户：写入 `audit_logs` 并删除 `users` 及级联数据。

## 6. 初始化数据

`sql/seed.sql` 初始化以下验收账号：

- 用户 `1001 / user1001`
- 用户 `1002 / user1002`
- 用户 `1003 / user1003`
- 管理员 `9001 / admin9001`

同时初始化好友分组、好友关系、朋友圈、评论和审计日志示例。
