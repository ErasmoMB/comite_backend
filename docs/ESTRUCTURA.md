comite_backend/
├── app/                              ← Código de la aplicación
│   ├── api/                          ← Endpoints REST
│   │   ├── auth/                     ✅ Autenticación
│   │   ├── users/                    ✅ Gestión de usuarios
│   │   ├── expedientes/              ✅ Expedientes (mejorado)
│   │   ├── evaluacion/               ✅ Evaluaciones + asignación manual
│   │   ├── dictamen/                 ✅ Dictámenes
│   │   ├── notificaciones/           ✅ Notificaciones
│   │   ├── reportes/                 ✅ Reportes
│   │   └── ia/                       ✅ IA
│   ├── core/                         ← Configuración principal
│   │   ├── config.py                 ✅ Settings
│   │   └── security.py               ✅ JWT, hashing
│   ├── db/                           ← Base de datos
│   │   └── database.py               ✅ Conexión PostgreSQL
│   ├── models/                       ← Modelos de BD
│   │   └── __init__.py               ✅ Todos los modelos
│   ├── schemas/                      ← Schemas Pydantic
│   │   └── __init__.py               ✅ Request/Response schemas
│   ├── services/                     ← Lógica de negocio (vacío, para futura expansión)
│   ├── utils/                        ← Utilidades (vacío, para futura expansión)
│   └── main.py                       ✅ App principal
│
├── env/                              ← Entorno virtual (mantener localmente)
│
├── .env                              ✅ Variables de entorno (Render PostgreSQL)
├── .env.example                      ✅ Plantilla actualizada con comentarios
├── .gitignore                        ✅ Actualizado (excluye uploads)
├── .dockerignore                     ✅ Para Docker
├── Dockerfile                        ✅ Para containerización
├── requirements.txt                  ✅ Dependencias Python
├── README.md                         ✅ Documentación completa
├── test_endpoints.py                 ✅ Script de pruebas
│
└── (ELIMINADOS)
    ✗ comite_v2.db                    BD SQLite antigua
    ✗ README copy.md                  Copia duplicada
    ✗ tests/                          Carpeta vacía
    ✗ uploads/                        Archivos de prueba
    ✗ __pycache__/                    Caché de Python