"""
Seed de credenciales demo para probar el login unificado y los roles nuevos.

Uso (desde la carpeta backend, con el venv activo):
    env/Scripts/python.exe seed_demo.py

Crea/actualiza un usuario por rol. Todos con la contraseña: password
Es idempotente: si el correo ya existe, solo actualiza rol y contraseña.
"""
from app.db.database import SessionLocal, init_db
from app.core.security import get_password_hash
from app.models import User

PASSWORD = "password"

# (correo, rol, nombre, apellido)
DEMO_USERS = [
    # --- Roles auto-registrables (misma vista funcional) ---
    ("pregrado@uch.edu.pe",   "estudiante_pregrado",  "Pamela",  "Pregrado"),
    ("postgrado@uch.edu.pe",  "estudiante_postgrado", "Pablo",   "Postgrado"),
    ("investigador@uch.edu.pe", "investigador",       "Ivan",    "Investigador"),
    # --- Roles internos (los crea el administrador) ---
    ("secretaria@uch.edu.pe",  "secretaria",    "Sofia",   "Secretaria"),
    ("coordinador@uch.edu.pe", "coordinador",   "Carlos",  "Coordinador"),
    ("evaluador@uch.edu.pe",   "evaluador",     "Elena",   "Evaluadora"),
    ("admin@uch.edu.pe",       "administrador", "Andrea",  "Admin"),
]


def main():
    init_db()  # asegura que las tablas existan
    db = SessionLocal()
    hashed = get_password_hash(PASSWORD)
    try:
        for correo, rol, nombre, apellido in DEMO_USERS:
            user = db.query(User).filter(User.email == correo).first()
            if user:
                user.rol = rol
                user.password_hash = hashed
                user.activo = True
                accion = "actualizado"
            else:
                user = User(
                    email=correo,
                    password_hash=hashed,
                    nombre=nombre,
                    apellido=apellido,
                    rol=rol,
                    activo=True,
                )
                db.add(user)
                accion = "creado"
            print(f"  [{accion}] {rol:22} -> {correo}")
        db.commit()
        print(f"\nListo. Todos con contraseña: {PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
