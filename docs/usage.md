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

语法检查：

```powershell
python -m py_compile src/moments_app.py
```

## 5. 已验证内容

- `src/moments_app.py` 通过 Python 语法检查。
- 静态契约测试 4 项通过。
- 数据库集成测试需要本地 MySQL 服务，验收前应先通过程序菜单执行初始化。
