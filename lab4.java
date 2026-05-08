import java.sql.Connection;
import java.sql.Date;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.sql.SQLException;
import java.sql.Statement;

class Lab4 {
    private static final String HOST = System.getenv().getOrDefault("MYSQL_HOST", "127.0.0.1");
    private static final String PORT = System.getenv().getOrDefault("MYSQL_PORT", "3306");
    private static final String USER = System.getenv().getOrDefault("MYSQL_USER", "root");
    private static final String PASSWORD = System.getenv().getOrDefault("MYSQL_PASSWORD", "123456");
    private static final String DATABASE = "library_lab4";

    public static void main(String[] args) {
        String serverUrl =
                "jdbc:mysql://" + HOST + ":" + PORT
                        + "/?serverTimezone=Asia/Shanghai&characterEncoding=UTF-8"
                        + "&useSSL=false&allowPublicKeyRetrieval=true";
        String databaseUrl =
                "jdbc:mysql://" + HOST + ":" + PORT + "/" + DATABASE
                        + "?serverTimezone=Asia/Shanghai&characterEncoding=UTF-8"
                        + "&useSSL=false&allowPublicKeyRetrieval=true";

        try {
            createDatabase(serverUrl);

            try (Connection conn = DriverManager.getConnection(databaseUrl, USER, PASSWORD)) {
                System.out.println("成功连接到数据库: " + DATABASE);

                createTables(conn);
                seedData(conn);

                printDivider("任务4: 查询学生表中的所有数据");
                printQuery(conn, "SELECT * FROM students ORDER BY student_id");

                printDivider("任务5: 多表查询 - 查询学生借书信息");
                printQuery(conn, """
                        SELECT br.record_id, s.student_name, b.book_name, br.borrow_date, br.status
                        FROM borrow_records br
                        JOIN students s ON br.student_id = s.student_id
                        JOIN books b ON br.book_id = b.book_id
                        ORDER BY br.record_id
                        """);

                printDivider("任务6: 修改某位学生年龄后，重新输出学生表");
                updateStudentAge(conn, 1003, 22);
                printQuery(conn, "SELECT * FROM students ORDER BY student_id");

                printDivider("任务7: 删除部分借阅记录后，重新输出借阅表");
                deleteReturnedBorrowRecords(conn);
                printQuery(conn, "SELECT * FROM borrow_records ORDER BY record_id");
            }
        } catch (SQLException e) {
            System.out.println("程序执行失败，请检查 MySQL 服务、账号密码、端口是否正确。");
            e.printStackTrace();
        }
    }

    private static void createDatabase(String serverUrl) throws SQLException {
        try (Connection conn = DriverManager.getConnection(serverUrl, USER, PASSWORD);
             Statement stmt = conn.createStatement()) {
            stmt.executeUpdate(
                    "CREATE DATABASE IF NOT EXISTS " + DATABASE
                            + " DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci");
            System.out.println("任务1+任务2: 已连接 MySQL，并确保数据库存在: " + DATABASE);
        }
    }

    private static void createTables(Connection conn) throws SQLException {
        try (Statement stmt = conn.createStatement()) {
            stmt.executeUpdate("""
                    CREATE TABLE IF NOT EXISTS students (
                        student_id INT PRIMARY KEY,
                        student_name VARCHAR(50) NOT NULL,
                        gender VARCHAR(10) NOT NULL,
                        age INT NOT NULL,
                        major VARCHAR(50) NOT NULL
                    )
                    """);

            stmt.executeUpdate("""
                    CREATE TABLE IF NOT EXISTS books (
                        book_id INT PRIMARY KEY,
                        book_name VARCHAR(100) NOT NULL,
                        author VARCHAR(50) NOT NULL,
                        category VARCHAR(50) NOT NULL,
                        stock INT NOT NULL
                    )
                    """);

            stmt.executeUpdate("""
                    CREATE TABLE IF NOT EXISTS borrow_records (
                        record_id INT PRIMARY KEY,
                        student_id INT NOT NULL,
                        book_id INT NOT NULL,
                        borrow_date DATE NOT NULL,
                        status VARCHAR(20) NOT NULL,
                        FOREIGN KEY (student_id) REFERENCES students(student_id),
                        FOREIGN KEY (book_id) REFERENCES books(book_id)
                    )
                    """);
            System.out.println("任务2: 3 张数据表创建完成。");
        }
    }

    private static void seedData(Connection conn) throws SQLException {
        // 先清空实验数据，保证程序可以重复运行且每次输出一致。
        try (Statement stmt = conn.createStatement()) {
            stmt.executeUpdate("DELETE FROM borrow_records");
            stmt.executeUpdate("DELETE FROM books");
            stmt.executeUpdate("DELETE FROM students");
        }

        try (PreparedStatement studentStmt = conn.prepareStatement(
                "INSERT INTO students(student_id, student_name, gender, age, major) VALUES (?, ?, ?, ?, ?)");
             PreparedStatement bookStmt = conn.prepareStatement(
                     "INSERT INTO books(book_id, book_name, author, category, stock) VALUES (?, ?, ?, ?, ?)");
             PreparedStatement borrowStmt = conn.prepareStatement(
                     "INSERT INTO borrow_records(record_id, student_id, book_id, borrow_date, status) VALUES (?, ?, ?, ?, ?)")) {

            insertStudent(studentStmt, 1001, "张明", "男", 20, "计算机科学");
            insertStudent(studentStmt, 1002, "李华", "女", 19, "软件工程");
            insertStudent(studentStmt, 1003, "王芳", "女", 21, "信息安全");
            insertStudent(studentStmt, 1004, "赵强", "男", 22, "人工智能");
            insertStudent(studentStmt, 1005, "陈雨", "女", 20, "数据科学");

            insertBook(bookStmt, 2001, "数据库系统概论", "王珊", "数据库", 6);
            insertBook(bookStmt, 2002, "Java 程序设计", "耿祥义", "编程", 5);
            insertBook(bookStmt, 2003, "计算机网络", "谢希仁", "网络", 4);
            insertBook(bookStmt, 2004, "操作系统原理", "汤小丹", "系统", 3);
            insertBook(bookStmt, 2005, "数据结构", "严蔚敏", "基础课", 7);

            insertBorrowRecord(borrowStmt, 3001, 1001, 2001, "2026-04-01", "借阅中");
            insertBorrowRecord(borrowStmt, 3002, 1002, 2002, "2026-04-03", "已归还");
            insertBorrowRecord(borrowStmt, 3003, 1003, 2005, "2026-04-05", "借阅中");
            insertBorrowRecord(borrowStmt, 3004, 1004, 2003, "2026-04-06", "已归还");
            insertBorrowRecord(borrowStmt, 3005, 1005, 2004, "2026-04-08", "借阅中");
        }

        System.out.println("任务3: 已为 3 张数据表分别插入 5 条数据。");
    }

    private static void updateStudentAge(Connection conn, int studentId, int newAge) throws SQLException {
        try (PreparedStatement stmt =
                     conn.prepareStatement("UPDATE students SET age = ? WHERE student_id = ?")) {
            stmt.setInt(1, newAge);
            stmt.setInt(2, studentId);
            int affectedRows = stmt.executeUpdate();
            System.out.println("已修改学生学号 " + studentId + " 的年龄，影响行数: " + affectedRows);
        }
    }

    private static void deleteReturnedBorrowRecords(Connection conn) throws SQLException {
        try (PreparedStatement stmt =
                     conn.prepareStatement("DELETE FROM borrow_records WHERE status = ?")) {
            stmt.setString(1, "已归还");
            int affectedRows = stmt.executeUpdate();
            System.out.println("已删除状态为'已归还'的借阅记录，影响行数: " + affectedRows);
        }
    }

    private static void printQuery(Connection conn, String sql) throws SQLException {
        try (Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery(sql)) {
            ResultSetMetaData metaData = rs.getMetaData();
            int columnCount = metaData.getColumnCount();

            for (int i = 1; i <= columnCount; i++) {
                System.out.printf("%-18s", metaData.getColumnLabel(i));
            }
            System.out.println();

            while (rs.next()) {
                for (int i = 1; i <= columnCount; i++) {
                    System.out.printf("%-18s", rs.getString(i));
                }
                System.out.println();
            }
        }
    }

    private static void insertStudent(
            PreparedStatement stmt, int id, String name, String gender, int age, String major)
            throws SQLException {
        stmt.setInt(1, id);
        stmt.setString(2, name);
        stmt.setString(3, gender);
        stmt.setInt(4, age);
        stmt.setString(5, major);
        stmt.executeUpdate();
    }

    private static void insertBook(
            PreparedStatement stmt, int id, String name, String author, String category, int stock)
            throws SQLException {
        stmt.setInt(1, id);
        stmt.setString(2, name);
        stmt.setString(3, author);
        stmt.setString(4, category);
        stmt.setInt(5, stock);
        stmt.executeUpdate();
    }

    private static void insertBorrowRecord(
            PreparedStatement stmt, int recordId, int studentId, int bookId, String borrowDate, String status)
            throws SQLException {
        stmt.setInt(1, recordId);
        stmt.setInt(2, studentId);
        stmt.setInt(3, bookId);
        stmt.setDate(4, Date.valueOf(borrowDate));
        stmt.setString(5, status);
        stmt.executeUpdate();
    }

    private static void printDivider(String title) {
        System.out.println();
        System.out.println("========== " + title + " ==========");
    }
}
