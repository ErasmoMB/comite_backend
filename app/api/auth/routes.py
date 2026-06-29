from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, decode_token
from app.core.config import settings
from app.models import User, ROLES_AUTO_REGISTRO
from app.schemas import Token, UserCreate, UserResponse, LoginRequest, LoginResponse

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    email = user.email if user.email else user.correo
    if not email:
        raise HTTPException(status_code=400, detail="Email es requerido")
    
    # Solo se permite auto-registrarse con los roles públicos.
    # Los roles internos (administrador, coordinador, secretaria, evaluador)
    # los crea únicamente el administrador vía POST /users.
    if user.rol not in ROLES_AUTO_REGISTRO:
        raise HTTPException(
            status_code=403,
            detail="Este rol no puede registrarse. Las credenciales de roles internos las crea el administrador.",
        )

    db_user = db.query(User).filter(User.email == email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email ya registrado")
    hashed_password = get_password_hash(user.password)
    
    nombre = user.nombres if user.nombres else (user.nombre or "")
    apellido = user.apellidos if user.apellidos else (user.apellido or "")
    
    if not nombre or not apellido:
        raise HTTPException(status_code=400, detail="Nombre y apellido son requeridos")

    # Validación de campos académicos según el rol:
    #  - estudiantes (pregrado/postgrado): código de estudiante obligatorio
    #  - investigador: laboratorio obligatorio
    es_estudiante = user.rol in ("estudiante_pregrado", "estudiante_postgrado")
    if es_estudiante and not (user.codigo_estudiante or "").strip():
        raise HTTPException(status_code=400, detail="El código de estudiante es obligatorio.")
    if user.rol == "investigador" and not (user.laboratorio or "").strip():
        raise HTTPException(status_code=400, detail="El laboratorio es obligatorio.")

    new_user = User(
        email=email,
        password_hash=hashed_password,
        nombre=nombre,
        apellido=apellido,
        rol=user.rol,
        especialidad=user.especialidad,
        carga_trabajo=user.carga_trabajo,
        conflicto_interes=user.conflicto_interes,
        # Solo se guarda el dato correspondiente al rol elegido.
        codigo_estudiante=user.codigo_estudiante if es_estudiante else None,
        laboratorio=user.laboratorio if user.rol == "investigador" else None,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta desactivada. Contacta al administrador.",
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


REDIRECT_BY_ROLE = {
    # Los 3 roles auto-registrables comparten la misma vista funcional.
    "investigador": "/investigador/dashboard",
    "estudiante_pregrado": "/investigador/dashboard",
    "estudiante_postgrado": "/investigador/dashboard",
    "estudiante": "/investigador/dashboard",  # legado
    # Roles internos: cada uno a su vista.
    "secretaria": "/secretaria/bandeja",
    "coordinador": "/coordinador/dashboard",
    "evaluador": "/evaluador/bandeja",
    "administrador": "/admin/configuracion",
}

@router.post("/login-json", response_model=LoginResponse)
def login_json(login_req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_req.correo).first()
    if not user or user.rol != login_req.rol:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas o rol no válido",
        )
    if not verify_password(login_req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta desactivada. Contacta al administrador.",
        )
    redirect_to = REDIRECT_BY_ROLE.get(user.rol, "/")
    return {"usuario": user, "redirectTo": redirect_to}

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Token inválido")
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token inválido")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user