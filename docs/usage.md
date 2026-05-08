# 运行说明

## 1. 环境准备

确认本机已启动 MySQL 服务，并准备好可创建数据库的账号。

程序默认读取以下环境变量：

- `MYSQL_HOST`，默认 `127.0.0.1`
- `MYSQL_PORT`，默认 `3306`
- `MYSQL_USER`，默认 `root`
- `MYSQL_PASSWORD`，默认 `123456`
- `MYSQL_DATABASE`，默认 `moments_lab`

如果本机 root 密码不是 `123456`，可在 PowerShell 中设置：

```powershell
$env:MYSQL_PASSWORD="你的MySQL密码"
```

## 2. 启动程序

### 命令行版本

在项目根目录执行：

```powershell
python src/moments_app.py
```

首次运行选择主菜单：

```text
1. 初始化数据库和验收数据
```

该操作会执行：

- `sql/schema.sql`：创建数据库、表、视图和触发器。
- `sql/seed.sql`：清空旧验收数据并初始化用户、管理员、朋友圈、评论等数据。

### 前端版本

在项目根目录执行：

```powershell
python src/web_app.py
```

默认访问：

```text
http://127.0.0.1:8000
```

如需修改端口：

```powershell
$env:WEB_PORT="8010"
python src/web_app.py
```

前端提供用户登录、管理员登录、注册、好友管理、分组管理、朋友圈发表/修改/删除、评论、管理员审核删除、注销用户和审计日志查看。

## 3. 验收账号

普通用户：

- `1001 / user1001`
- `1002 / user1002`
- `1003 / user1003`

管理员：

- `9001 / admin9001`

## 4. 测试命令

静态契约测试：

```powershell
python -m unittest discover -s tests
```

真实 MySQL 集成测试默认跳过。如需验证实际数据库操作，先确认 MySQL 服务和账号可用，然后执行：

```powershell
$env:RUN_DB_TESTS="1"
$env:MYSQL_DATABASE="moments_lab_test"
python -m unittest tests.test_database_integration
```

该测试会使用 `moments_lab_test`，自动执行建表和初始化数据，并验证真实登录、注册事务、双向好友、朋友圈触发器、评论级联删除、管理员审核视图和审计日志。

语法检查：

```powershell
python -m py_compile src/moments_app.py
```

## 5. 已验证内容

- `src/moments_app.py` 通过 Python 语法检查。
- `src/web_app.py` 通过 Python 语法检查。
- 默认测试包含静态契约、SQL 契约、前端契约、需求对照和默认跳过的数据库集成测试。
- 数据库集成测试需要本地 MySQL 服务，设置 `RUN_DB_TESTS=1` 后会实际操作 `moments_lab_test`。
