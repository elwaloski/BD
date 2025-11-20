import pyodbc
import configparser
from datetime import datetime
import ast


def log(mensaje: str):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {mensaje}")


def crear_usuario_sql(server, database, sa_user, sa_password, login_name, login_password, user_name, roles):
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE=master;"
        f"UID={sa_user};"
        f"PWD={sa_password};"
    )

    try:
        log("Conectando a SQL Server...")
        conn = pyodbc.connect(conn_str, autocommit=True)
        cursor = conn.cursor()
        log("✔ Conexión establecida")

        # LOGIN
        log(f"Creando login '{login_name}' si no existe...")
        cursor.execute(f"""
            IF NOT EXISTS(SELECT * FROM sys.server_principals WHERE name = '{login_name}')
            BEGIN
                CREATE LOGIN [{login_name}] WITH PASSWORD = '{login_password}';
            END;
        """)
        log("✔ Login creado/verificado")

        # USER
        cursor.execute(f"USE {database};")
        log(f"Creando usuario '{user_name}' en la BD...")
        cursor.execute(f"""
            IF NOT EXISTS(SELECT * FROM sys.database_principals WHERE name = '{user_name}')
            BEGIN
                CREATE USER [{user_name}] FOR LOGIN [{login_name}];
            END;
        """)
        log("✔ Usuario creado/verificado")

        # ROLES
        for rol in roles:
            log(f"Asignando rol '{rol}'...")
            cursor.execute(f"USE {database};")
            cursor.execute(f"EXEC sp_addrolemember '{rol}', '{user_name}';")
            log(f"✔ Rol asignado: {rol}")

        log("🎉 Proceso finalizado correctamente")

    except Exception as e:
        log(f"❌ Error: {e}")

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

    # Sección DATABASE
    server = config["DATABASE"]["server"]
    database = config["DATABASE"]["database"]
    sa_user = config["DATABASE"]["UserBD"]
    sa_password = config["DATABASE"]["PASSBD"]

    # Sección NEWUSER
    login_name = config["NEWUSER"]["login_name"]
    login_password = config["NEWUSER"]["login_password"]
    user_name = config["NEWUSER"]["user_name"]

    # Convertir la cadena "[db_owner, db_datareader]" en lista real
    roles_raw = config["NEWUSER"]["roles"]
    roles = ast.literal_eval(roles_raw)   # Convierte string → lista de Python

    log(f"Roles cargados desde el archivo: {roles}")

    # Ejecutar creación
    crear_usuario_sql(
        server=server,
        database=database,
        sa_user=sa_user,
        sa_password=sa_password,
        login_name=login_name,
        login_password=login_password,
        user_name=user_name,
        roles=roles
    )


if __name__ == "__main__":
    main()
