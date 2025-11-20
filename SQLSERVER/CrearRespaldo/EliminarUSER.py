import pyodbc
import configparser
from datetime import datetime


def log(mensaje: str):
    """Imprime mensajes en consola con timestamp."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {mensaje}")


def eliminar_usuario_sql(server, database, sa_user, sa_password, user_name, login_name):
    """Elimina un usuario de base de datos y su login asociado en SQL Server."""

    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE=master;"
        f"UID={sa_user};"
        f"PWD={sa_password};"
    )

    try:
        log("Conectando al servidor SQL...")
        conn = pyodbc.connect(conn_str, autocommit=True)
        cursor = conn.cursor()
        log("✔ Conexión establecida")

        # 1. Eliminar USUARIO dentro de la BD
        log(f"Intentando eliminar usuario '{user_name}' de la BD '{database}'...")
        cursor.execute(f"USE {database};")
        cursor.execute(f"""
            IF EXISTS (SELECT * FROM sys.database_principals WHERE name = '{user_name}')
            BEGIN
                DROP USER [{user_name}];
            END;
        """)
        log("✔ Usuario eliminado (si existía)")

        # 2. Eliminar LOGIN en el servidor
        log(f"Intentando eliminar login '{login_name}' del servidor...")
        cursor.execute(f"""
            IF EXISTS (SELECT * FROM sys.server_principals WHERE name = '{login_name}')
            BEGIN
                DROP LOGIN [{login_name}];
            END;
        """)
        log("✔ Login eliminado (si existía)")

        log("🎉 Eliminación completada correctamente")

    except Exception as e:
        log(f"❌ Error durante la eliminación: {e}")

    finally:
        try:
            conn.close()
            log("Conexión cerrada.")
        except:
            pass


def main():
    log("Leyendo archivo de configuración...")
    config = configparser.ConfigParser()
    config.read("config.ini")

    # Datos de conexión
    server = config["DATABASE"]["server"]
    database = config["DATABASE"]["database"]
    sa_user = config["DATABASE"]["UserBD"]
    sa_password = config["DATABASE"]["PASSBD"]

    # Datos del usuario a eliminar
    user_name = config["DELETEUSER"]["user_name"]
    login_name = config["DELETEUSER"]["login_name"]

    log(f"Usuario a eliminar: {user_name}")
    log(f"Login a eliminar: {login_name}")

    eliminar_usuario_sql(
        server=server,
        database=database,
        sa_user=sa_user,
        sa_password=sa_password,
        user_name=user_name,
        login_name=login_name
    )


if __name__ == "__main__":
    main()
