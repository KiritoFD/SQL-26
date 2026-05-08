# 实验要求逐项对照表

## 1. 基本实现方式

| 实验要求 | 实现位置 | 测试位置 | 状态 |
| --- | --- | --- | --- |
| 基于高级语言 | `src/moments_app.py`、`src/web_app.py` 使用 Python | `tests/test_static_contract.py` | 已覆盖 |
| 使用 MySQL | `mysql.connector`、`sql/schema.sql` | `tests/test_static_contract.py` | 已覆盖 |
| 至少一种交互方式 | 命令行与 Web 前端均已提供 | `tests/test_web_contract.py` | 已覆盖 |
| 初始化验收数据 | `sql/seed.sql` | `tests/test_requirement_alignment.py` | 已覆盖 |

## 2. 用户端逐项对照

| 原始要求 | 需求编号 | 实现位置 | 测试位置 | 状态 |
| --- | --- | --- | --- | --- |
| 用户可以注册，初始化用户 id 和密码 | R-USER-001 | `register_user`、`/api/register` | `test_requirement_alignment.py` | 已覆盖 |
| 用户可以登录 | R-USER-002 | `login_user`、`/api/login/user` | `test_requirement_alignment.py` | 已覆盖 |
| 修改姓名、性别、出生日期、年龄 | R-USER-003 | `update_user_profile`、`/api/profile` | `test_requirement_alignment.py` | 已覆盖 |
| 搜索好友 | R-FRIEND-001 | `search_users`、`/api/users/search` | `test_requirement_alignment.py` | 已覆盖 |
| 添加好友 | R-FRIEND-002 | `add_friend`、`/api/friends` | `test_requirement_alignment.py` | 已覆盖 |
| 删除好友 | R-FRIEND-003 | `delete_friend`、`DELETE /api/friends/{id}` | `test_requirement_alignment.py` | 已覆盖 |
| 好友分组管理 | R-FRIEND-004 | `friend_groups`、`create_group`、`move_friend` | `test_sql_contract.py` | 已覆盖 |
| 发表朋友圈，字数限制 | R-MOMENT-001 | `moments`、`create_moment`、前端 `maxlength=280` | `test_requirement_alignment.py` | 已覆盖 |
| 修改朋友圈，记录最后更新时间 | R-MOMENT-002 | `update_moment`、`trg_moments_before_update` | `test_sql_contract.py` | 已覆盖 |
| 查看好友朋友圈和评论 | R-MOMENT-004 | `v_friend_moments`、`/api/moments/friends`、`/api/comments` | `test_web_contract.py` | 已覆盖 |
| 评论好友朋友圈 | R-COMMENT-001 | `comment_moment`、`/api/comments` | `test_requirement_alignment.py` | 已覆盖 |
| 删除自己的朋友圈并自动删除评论 | R-MOMENT-003 | `delete_moment`、`fk_comments_moment ON DELETE CASCADE` | `test_sql_contract.py` | 已覆盖 |

## 3. 管理员端逐项对照

| 原始要求 | 需求编号 | 实现位置 | 测试位置 | 状态 |
| --- | --- | --- | --- | --- |
| 管理员 id 和密码 | R-ADMIN-001 | `admins`、`/api/login/admin`、`seed.sql` | `test_requirement_alignment.py` | 已覆盖 |
| 管理员登录 | R-ADMIN-001 | `login_admin`、`/api/login/admin` | `test_web_contract.py` | 已覆盖 |
| 修改管理员个人信息 | R-ADMIN-002 | `update_admin_profile`、`/api/admin/profile` | `test_requirement_alignment.py` | 已覆盖 |
| 注销用户并删除相关信息 | R-ADMIN-005 | `admin_disable_user`、外键级联删除 | `test_requirement_alignment.py` | 已覆盖 |
| 管理员不可浏览用户个人基本信息 | R-ADMIN-003 | `v_admin_moments` 不含姓名、性别、生日、年龄、密码 | `test_sql_contract.py` | 已覆盖 |
| 管理员浏览全部朋友圈审核 | R-ADMIN-003 | `v_admin_moments`、`/api/admin/moments` | `test_web_contract.py` | 已覆盖 |
| 管理员删除朋友圈 | R-ADMIN-004 | `admin_delete_moment`、审计日志 | `test_requirement_alignment.py` | 已覆盖 |

## 4. 数据库课程要求对照

| 实验要求 | 实现位置 | 测试位置 | 状态 |
| --- | --- | --- | --- |
| 合适的表结构 | `sql/schema.sql` 七张核心表 | `test_sql_contract.py` | 已覆盖 |
| 完整性约束 | 主键、外键、唯一约束、CHECK、ENUM、NOT NULL | `test_sql_contract.py` | 已覆盖 |
| 视图 | `v_admin_moments`、`v_friend_moments` | `test_sql_contract.py` | 已覆盖 |
| 事务管理 | 注册、添加好友、管理员删除、注销用户 | `test_requirement_alignment.py` | 已覆盖 |
| 触发器 | `trg_moments_before_update`、`trg_comments_after_insert` | `test_sql_contract.py` | 已覆盖 |
| 插入/删除/修改/查询逻辑 | CLI 函数、Web API、前端页面 | `test_web_contract.py` | 已覆盖 |
| 错误处理机制 | `ApiError`、异常回滚、HTTP 状态码、前端 toast | `test_web_contract.py` | 已覆盖 |

## 5. 当前测试结论

已执行：

```powershell
python -m py_compile src/moments_app.py src/web_app.py
python -m unittest discover -s tests
```

结果：20 项测试全部通过。

说明：当前自动化测试属于静态契约与实现对照测试，不依赖 MySQL 服务。真实数据库联调仍需在本机 MySQL 启动后，通过前端或命令行执行初始化并按 `docs/test_plan.md` 的功能用例验收。
