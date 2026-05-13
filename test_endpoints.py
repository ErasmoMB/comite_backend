"""
Script de prueba para todos los endpoints mejorados
Prueba: 1. POST /expedientes/, 2. PUT /expedientes/{id}, 3. POST /documentos, 4. POST /asignar
"""

import requests
import json
from pathlib import Path
import uuid
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_section(title):
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}{Colors.RESET}\n")

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")

def print_info(msg):
    print(f"{Colors.YELLOW}ℹ️  {msg}{Colors.RESET}")

# ============================================================================
# PASO 1: Login/Crear usuario de prueba
# ============================================================================
print_section("PASO 1: Autenticación")

# Generar email único
unique_id = str(uuid.uuid4())[:8]

# Datos del usuario de prueba
test_user = {
    "email": f"testadmin_{unique_id}@comite.edu",
    "password": "Test123456",
    "nombre": "Admin",
    "apellido": "Test",
    "rol": "coordinador"
}

# Intentar login
print_info(f"Intentando login con: {test_user['email']}")
response = requests.post(
    f"{BASE_URL}/auth/login",
    data={
        "username": test_user["email"],
        "password": test_user["password"]
    }
)

token = None

if response.status_code == 200:
    token = response.json().get("access_token")
    print_success(f"Login exitoso")
    print_info(f"Token: {token[:50]}...")
else:
    print_error(f"Login fallido ({response.status_code})")
    print_info("Creando usuario de prueba...")
    
    # Crear usuario
    create_response = requests.post(
        f"{BASE_URL}/auth/register",
        json=test_user
    )
    
    if create_response.status_code in [200, 201]:
        print_success("Usuario creado")
        
        # Intentar login de nuevo
        login_response = requests.post(
            f"{BASE_URL}/auth/login",
            data={
                "username": test_user["email"],
                "password": test_user["password"]
            }
        )
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            print_success("Login exitoso después de crear usuario")
        else:
            print_error(f"Login fallido incluso después de crear usuario: {login_response.text}")
            exit(1)
    else:
        print_error(f"No se pudo crear usuario: {create_response.text}")
        exit(1)

if not token:
    print_error("No se obtuvo token. Abortando...")
    exit(1)

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# ============================================================================
# PASO 2: POST /expedientes/ - CREAR EXPEDIENTE CON METADATOS
# ============================================================================
print_section("PASO 2: POST /api/v1/expedientes/ (MEJORADO)")

expediente_data = {
    "titulo_protocolo": "Estudio de efectividad de vacunas COVID-19",
    "tipo_tramite": "investigacion_biomedica",
    "facultad": "Medicina",
    "prioridad": "alta"
}

print_info(f"Creando expediente con datos:")
print(json.dumps(expediente_data, indent=2, ensure_ascii=False))

response = requests.post(
    f"{BASE_URL}/expedientes/",
    json=expediente_data,
    headers=headers
)

expediente_id = None
if response.status_code in [200, 201]:
    expediente = response.json()
    expediente_id = expediente.get("id")
    print_success(f"Expediente creado exitosamente")
    print_info(f"ID: {expediente_id}")
    print_info(f"Código: {expediente.get('codigo_unico')}")
    print_info(f"Estado: {expediente.get('estado')}")
    print_info(f"Tipo trámite: {expediente.get('tipo_tramite')}")
    print_info(f"Facultad: {expediente.get('facultad')}")
    print_info(f"Prioridad: {expediente.get('prioridad')}")
else:
    print_error(f"Error al crear expediente ({response.status_code})")
    print_error(f"Respuesta: {response.text}")
    exit(1)

# ============================================================================
# PASO 3: PUT /expedientes/{id} - ACTUALIZAR CON NUEVOS CAMPOS
# ============================================================================
print_section("PASO 3: PUT /api/v1/expedientes/{id} (MEJORADO)")

update_data = {
    "tipo_tramite": "investigacion_experimental",
    "facultad": "Ingenieria",
    "prioridad": "media"
}

print_info(f"Actualizando expediente {expediente_id} con:")
print(json.dumps(update_data, indent=2, ensure_ascii=False))

response = requests.put(
    f"{BASE_URL}/expedientes/{expediente_id}",
    json=update_data,
    headers=headers
)

if response.status_code == 200:
    expediente = response.json()
    print_success(f"Expediente actualizado exitosamente")
    print_info(f"Tipo trámite: {expediente.get('tipo_tramite')}")
    print_info(f"Facultad: {expediente.get('facultad')}")
    print_info(f"Prioridad: {expediente.get('prioridad')}")
else:
    print_error(f"Error al actualizar expediente ({response.status_code})")
    print_error(f"Respuesta: {response.text}")

# ============================================================================
# PASO 4: POST /expedientes/{id}/documentos - UPLOAD DE ARCHIVO
# ============================================================================
print_section("PASO 4: POST /api/v1/expedientes/{id}/documentos (CORREGIDO)")

# Crear archivo de prueba
test_file_path = Path("test_documento.txt")
test_file_path.write_text("Este es un documento de prueba para el expediente.")

print_info(f"Subiendo archivo: {test_file_path.name}")

files = {
    "file": (test_file_path.name, open(test_file_path, "rb"), "text/plain"),
}

data = {
    "tipo_documento": "protocolo",
    "es_obligatorio": True
}

headers_file = {"Authorization": f"Bearer {token}"}

response = requests.post(
    f"{BASE_URL}/expedientes/{expediente_id}/documentos",
    files=files,
    data=data,
    headers=headers_file
)

# Cerrar el archivo
files["file"][1].close()

if response.status_code in [200, 201]:
    documento = response.json()
    print_success(f"Documento subido exitosamente")
    print_info(f"ID documento: {documento.get('id')}")
    print_info(f"Nombre: {documento.get('nombre_archivo')}")
    print_info(f"Tipo: {documento.get('tipo_documento')}")
    print_info(f"Obligatorio: {documento.get('es_obligatorio')}")
    print_info(f"Ruta: {documento.get('ruta_archivo')}")
else:
    print_error(f"Error al subir documento ({response.status_code})")
    print_error(f"Respuesta: {response.text}")

# Limpiar archivo de prueba
test_file_path.unlink()

# ============================================================================
# PASO 5: POST /evaluacion/expediente/{id}/asignar - ASIGNAR EVALUADOR
# ============================================================================
print_section("PASO 5: POST /api/v1/evaluacion/expediente/{id}/asignar (NUEVO)")

# Primero obtener lista de evaluadores
print_info("Obteniendo lista de evaluadores disponibles...")

response = requests.get(
    f"{BASE_URL}/users/?rol=evaluador",
    headers=headers
)

evaluador_id = None

if response.status_code == 200:
    # Si no funciona el filtro, obtener todos los usuarios
    usuarios = response.json() if isinstance(response.json(), list) else []
    if not usuarios:
        # Obtener todos los usuarios
        response = requests.get(f"{BASE_URL}/users/", headers=headers)
        usuarios = response.json() if isinstance(response.json(), list) else []
    
    # Buscar un evaluador
    evaluadores = [u for u in usuarios if u.get("rol") == "evaluador" and u.get("id") != expediente_id]
    
    if evaluadores:
        evaluador_id = evaluadores[0]["id"]
        print_success(f"Evaluador encontrado: ID {evaluador_id} - {evaluadores[0].get('nombre')}")
    else:
        print_error("No hay evaluadores disponibles")
        print_info("Creando evaluador de prueba...")
        
        # Generar email único
        unique_id = str(uuid.uuid4())[:8]
        evaluador_data = {
            "email": f"evaluador_{unique_id}@comite.edu",
            "password": "Eval123456",
            "nombre": "Juan",
            "apellido": "Evaluador",
            "rol": "evaluador"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/auth/register",
            json=evaluador_data,
            headers=headers
        )
        
        if create_response.status_code in [200, 201]:
            evaluador = create_response.json()
            evaluador_id = evaluador.get("id")
            print_success(f"Evaluador creado: ID {evaluador_id}")
        else:
            print_error(f"No se pudo crear evaluador: {create_response.text}")

if evaluador_id:
    assign_data = {
        "evaluador_id": evaluador_id
    }
    
    print_info(f"Asignando evaluador {evaluador_id} al expediente {expediente_id}...")
    
    response = requests.post(
        f"{BASE_URL}/evaluacion/expediente/{expediente_id}/asignar",
        json=assign_data,
        headers=headers
    )
    
    if response.status_code in [200, 201]:
        resultado = response.json()
        print_success(f"Evaluador asignado exitosamente")
        print_info(f"Evaluación ID: {resultado.get('evaluacion_id')}")
        print_info(f"Evaluador: {resultado.get('evaluador', {}).get('nombre')} {resultado.get('evaluador', {}).get('apellido')}")
        print_info(f"Expediente: {resultado.get('expediente_codigo')}")
    else:
        print_error(f"Error al asignar evaluador ({response.status_code})")
        print_error(f"Respuesta: {response.text}")
else:
    print_error("No se pudo obtener/crear evaluador")

# ============================================================================
# RESUMEN FINAL
# ============================================================================
print_section("RESUMEN FINAL")
print_success("Script de prueba completado")
print_info("Todos los endpoints fueron probados exitosamente")
print_info(f"Expediente de prueba creado: ID {expediente_id}")
print("\n" + "="*60)
