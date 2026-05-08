# 源码结构说明

`src` 已按职责拆分，避免把数据库、业务、交互和 Web 路由全部塞进入口脚本。

## 模块划分

- `src/moments_app.py`：命令行启动入口，放演示用环境变量默认值，然后启动 CLI。
- `src/web_app.py`：Web 启动入口，放数据库与 Web 服务默认配置，然后启动 HTTP 服务。
- `src/moments/config.py`：集中读取环境变量和项目路径。
- `src/moments/db.py`：MySQL 连接、密码哈希、通用查询、写入和事务上下文。
- `src/moments/sql_runner.py`：执行 `schema.sql`、`seed.sql`，处理 MySQL `DELIMITER` 脚本。
- `src/moments/services.py`：业务规则层，包含注册、登录、好友、朋友圈、评论、管理员审核和注销用户。
- `src/moments/cli.py`：命令行输入输出和菜单，不直接承载业务规则。
- `src/moments/web.py`：HTTP API、Session、角色校验和静态文件服务，不直接拼写复杂业务事务。
- `src/web/`：Web 前端静态资源，包含 `index.html`、`styles.css`、`app.js`。

## 设计原则

- 入口脚本只负责启动配置和调用应用，不放数据库事务和业务规则。
- Web 和 CLI 共享 `services.py`，避免两套逻辑不一致。
- 数据库连接和事务集中在 `db.py`，失败时统一回滚。
- SQL 初始化集中在 `sql_runner.py`，便于验收时单独展示数据库脚本。
- 测试同步检查模块边界，防止后续重新退化成长文件。
