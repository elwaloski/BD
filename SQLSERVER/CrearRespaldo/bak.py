import subprocess
import os
import zipfile
import configparser
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import shutil



def enviar_correo(cfg, asunto, mensaje, log_path):
    try:
        write_log(log_path, "Enviando correo...")

        msg = MIMEMultipart()
        msg["From"] = cfg["email_from"]
        msg["To"] = cfg["email_to"]
        msg["Subject"] = asunto

        msg.attach(MIMEText(mensaje, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(cfg["email_from"], cfg["email_pass"])
        server.send_message(msg)
        server.quit()

        write_log(log_path, "✔ Correo enviado correctamente.")

    except Exception as e:
        write_log(log_path, f"❌ ERROR enviando correo: {e}")

# ------------------------------------------------------------
# 1) Cargar configuración desde config.ini
# ------------------------------------------------------------
def cargar_config():
    config = configparser.ConfigParser()
    config.read("config.ini")

    return {
        "server": config["DATABASE"]["SERVER"],
        "database": config["DATABASE"]["database"],
        "backup_folder": config["DATABASE"]["BACKUP_FOLDER"],
        "email_from": config["EMAIL"]["FROM"],
        "email_to": config["EMAIL"]["TO"],
        "email_pass": config["EMAIL"]["password"],
        "destino_backup": config["MOVE"]["DESTINO_BACKUP"]   # ← NUEVO
    }


# ------------------------------------------------------------
# 2) Escribir log
# ------------------------------------------------------------
def write_log(log_path, msg):
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(msg + "\n")
    print(msg)


# ------------------------------------------------------------
# 3) Crear backup usando sqlcmd
# ------------------------------------------------------------
def ejecutar_backup(server, database, bak_path, log_path):

    sqlcmd_command = [
        "sqlcmd",
        "-S", server,
        "-Q", f"BACKUP DATABASE {database} TO DISK='{bak_path}' WITH INIT"
    ]

    write_log(log_path, f"Ejecutando backup → {bak_path}")

    result = subprocess.run(sqlcmd_command, capture_output=True, text=True)

    if result.stdout:
        write_log(log_path, "STDOUT:\n" + result.stdout)

    if result.stderr:
        write_log(log_path, "STDERR:\n" + result.stderr)

    return os.path.exists(bak_path)


# ------------------------------------------------------------
# 4) Comprimir archivo .bak a .zip
# ------------------------------------------------------------
def crear_zip(bak_path, zip_path, log_path):
    write_log(log_path, "Comprimiendo en ZIP...")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(bak_path, os.path.basename(bak_path))

    write_log(log_path, f"ZIP creado: {zip_path}")


# ------------------------------------------------------------
# 5) Mover archivos a ruta destino
# ------------------------------------------------------------
def mover_archivos(bak_path, zip_path, destino, log_path):
    try:
        if not os.path.exists(destino):
            os.makedirs(destino)
            write_log(log_path, f"Carpeta destino creada: {destino}")

        bak_dest = os.path.join(destino, os.path.basename(bak_path))
        zip_dest = os.path.join(destino, os.path.basename(zip_path))

        shutil.move(bak_path, bak_dest)
        shutil.move(zip_path, zip_dest)

        write_log(log_path, f"✔ Archivos movidos a {destino}")

        return bak_dest, zip_dest

    except Exception as e:
        write_log(log_path, f"❌ ERROR moviendo archivos: {e}")
        return None, None


# ------------------------------------------------------------
# 6) MAIN
# ------------------------------------------------------------
def main():
    cfg = cargar_config()

    fecha = datetime.now().strftime("%Y%m%d_%H%M")

    bak_name = f"{cfg['database']}_{fecha}.bak"
    bak_path = os.path.join(cfg["backup_folder"], bak_name)

    zip_path = bak_path.replace(".bak", ".zip")

    log_name = f"log_{fecha}.log"
    log_path = os.path.join(cfg["backup_folder"], log_name)

    write_log(log_path, "=== INICIO BACKUP ===")

    # Ejecutar backup
    exito = ejecutar_backup(cfg["server"], cfg["database"], bak_path, log_path)

    if exito:
        write_log(log_path, f"✔ Backup generado: {bak_path}")
        crear_zip(bak_path, zip_path, log_path)

        # -------- MOVER A DESTINO --------
        bak_final, zip_final = mover_archivos(
            bak_path, zip_path, cfg["destino_backup"], log_path
        )

    else:
        write_log(log_path, "❌ ERROR: No se creó el archivo .bak")

    # Enviar correo
    if exito:
        enviar_correo(
            cfg,
            "Backup exitoso",
            f"El backup de la base {cfg['database']} se generó correctamente.\n\n"
            f"Rutas finales:\n{bak_final}\n{zip_final}",
            log_path
        )
    else:
        enviar_correo(
            cfg,
            "Error en backup",
            f"No se pudo generar el backup de la base {cfg['database']}.\n\nRevisar log:\n{log_path}",
            log_path
        )

    write_log(log_path, "=== FIN BACKUP ===")

# ------------------------------------------------------------
# Ejecución directa
# ------------------------------------------------------------
if __name__ == "__main__":
    main()
