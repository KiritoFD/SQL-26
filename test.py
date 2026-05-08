try:
    import mysql.connector
    from mysql.connector import Error
except ImportError as e:
    print("MySQL Python driver not found. Install with: pip install mysql-connector-python")
    raise


def main() -> None:
    host = "127.0.0.1"
    port = 3306
    user = "root"
    password = "xy"

    conn = None
    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password
        )

        print("Connected to MySQL successfully.")

        with conn.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            rows = cursor.fetchone()
            version = rows[0] if rows else None
            print(f"MySQL version: {version}")


    except Error:
        print("Connection failed. Check MySQL service/user/password.")
        raise
    finally:
        if conn is not None and conn.is_connected():
            conn.close()
            print("Connection closed.")


if __name__ == "__main__":
    main()


