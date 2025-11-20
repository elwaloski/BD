import subprocess
import os
import zipfile
import configparser
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import shutil


# ------------------------------------------------------------
# Enviar correo
# ------------------------------------------------------------
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
# Obtener ruta default SQL Server (si se necesita)
# ------------------------------------------------------------
def obtener_ruta_backup(server):
    cmd = [
        "sqlcmd",
        "-S", server,
        "-h", "-1",
        "-W",
        "-Q",
        """
        SET NOCOUNT ON;
        EXEC master.dbo.xp_instance_regread
            'HKEY_LOCAL_MACHINE',
            'Software\\Microsoft\\MSSQLServer\\MSSQLServer',
            'BackupDirectory';
        """
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return None

    lines = result.stdout.splitlines()
    clean = [l.strip() for l in lines if l.strip()]

    for line in clean:
        if ":" in line and "\\" in line:
            return line.strip()

    return None


# ------------------------------------------------------------
# Log
# ------------------------------------------------------------
def write_log(log_path, msg):
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(msg + "\n")
    print(msg)


# ------------------------------------------------------------
# Config
# ------------------------------------------------------------
def cargar_config():
    config = configparser.ConfigParser()
    config.read("config.ini")

    return {
        "server": config["DATABASE"]["SERVER"],
        "database": config["DATABASE"]["DATABASE"],
        "RutaBak": config["DATABASE"]["RutaBak"],  # ruta por defecto SQL
        "destino_copia": config["DATABASE"]["backup_folder"],
        "email_from": config["EMAIL"]["FROM"],
        "email_to": config["EMAIL"]["TO"],
        "email_pass": config["EMAIL"]["password"]
    }


# ------------------------------------------------------------
# Crear backup en ruta por defecto SQL
# ------------------------------------------------------------
def crear_backup_ruta_defecto(server, database, ruta_defecto, log_path):
    fecha = datetime.now().strftime("%Y%m%d_%H%M")
    bak_name = f"{database}_{fecha}.bak"
    bak_path = os.path.join(ruta_defecto, bak_name)

    comando = [
        "sqlcmd",
        "-S", server,
        "-Q", f"BACKUP DATABASE {database} TO DISK='{bak_path}' WITH INIT"
    ]

    write_log(log_path, f"Generando backup en ruta por defecto:\n{bak_path}")

    result = subprocess.run(comando, capture_output=True, text=True)

    if result.stdout:
        write_log(log_path, "STDOUT:\n" + result.stdout)

    if result.stderr:
        write_log(log_path, "STDERR:\n" + result.stderr)

    return bak_path if os.path.exists(bak_path) else None


# ------------------------------------------------------------
# Copiar archivo .bak
# ------------------------------------------------------------
def copiar_backup(bak_path, destino, log_path):
    if not os.path.exists(destino):
        os.makedirs(destino)

    dest_path = os.path.join(destino, os.path.basename(bak_path))
    shutil.copy2(bak_path, dest_path)

    write_log(log_path, f"Backup copiado a ruta secundaria:\n{dest_path}")
    return dest_path


# ------------------------------------------------------------
# Crear ZIP
# ------------------------------------------------------------
def crear_zip_en_destino(bak_copiado, log_path):
    zip_path = bak_copiado.replace(".bak", ".zip")

    write_log(log_path, f"Creando ZIP:\n{zip_path}")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(bak_copiado, os.path.basename(bak_copiado))

    return zip_path


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main():

    cfg = cargar_config()
    fecha = datetime.now().strftime("%Y%m%d_%H%M")

    log_name = f"log_{fecha}.log"
    log_path = os.path.join(cfg["destino_copia"], log_name)

    write_log(log_path, "=== INICIO BACKUP ===")

    # 1) Crear backup en ruta por defecto SQL
    bak_defecto = crear_backup_ruta_defecto(
        cfg["server"],
        cfg["database"],
        cfg["RutaBak"],
        log_path
    )

    if not bak_defecto:
        write_log(log_path, "❌ ERROR: No se generó el backup en la ruta por defecto.")
        return

    # 2) Copiar a la ruta secundaria
    bak_copiado = copiar_backup(bak_defecto, cfg["destino_copia"], log_path)

    # 3) Crear ZIP
    zip_file = crear_zip_en_destino(bak_copiado, log_path)

    write_log(log_path, "=== PROCESO FINALIZADO ===")
    write_log(log_path, f"Backup original : {bak_defecto}")
    write_log(log_path, f"Backup copiado  : {bak_copiado}")
    write_log(log_path, f"ZIP generado    : {zip_file}")
    write_log(log_path, "===========================")

    # 4) Enviar correo
    mensaje = (
        f"Estimad@s,\n\n"
        f"Backup exitoso - Base de Datos: {cfg['database']}\n\n"
        f"El backup de la base {cfg['database']} se generó correctamente.\n\n"
        f"Ruta del backup copiado:\n{bak_copiado}\n\n"
        f"Archivo ZIP generado:\n{zip_file}\n\n"
        f"Saludos Cordiales\n"
    )

    enviar_correo(cfg, "Backup exitoso", mensaje, log_path)

# Ejecutar
if __name__ == "__main__":
    main()
