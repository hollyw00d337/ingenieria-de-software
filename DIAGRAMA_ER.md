# 📊 DIAGRAMA ENTIDAD-RELACIÓN
# Base de datos: plate_recognition_db

```
                    ┌─────────────────────────────────┐
                    │             USERS               │
                    │─────────────────────────────────│
                    │ 🔑 id (PK) - INTEGER            │
                    │ 🆔 user_id (UNIQUE) - VARCHAR   │
                    │    username (UNIQUE) - VARCHAR  │
                    │    password_hash - VARCHAR      │
                    │    full_name - VARCHAR          │
                    │    occupation - VARCHAR         │
                    │    role - VARCHAR               │
                    │    created_at - DATETIME        │
                    │    is_active - BOOLEAN          │
                    └─────────────┬───────────────────┘
                                  │ 1
                                  │
                                  │ N
                    ┌─────────────▼───────────────────┐
                    │           VEHICLES              │
                    │─────────────────────────────────│
                    │ 🔑 id (PK) - INTEGER            │
                    │    plate_number (UNIQUE) - VAR  │
                    │ 🔗 user_id (FK) - INTEGER       │
                    │    created_at - DATETIME        │
                    │    is_active - BOOLEAN          │
                    └─────────────────────────────────┘
                                  
┌─────────────────────────────────┐        ┌─────────────────────────────────┐
│          ACCESS_LOGS            │        │            ALERTS               │
│─────────────────────────────────│        │─────────────────────────────────│
│ 🔑 id (PK) - INTEGER            │        │ 🔑 id (PK) - INTEGER            │
│    plate_number - VARCHAR       │   1    │ 🔗 access_log_id (FK) - INT     │
│ 🔗 user_id (FK) - INTEGER       │◄───────┤    alert_type - VARCHAR         │
│    timestamp - DATETIME         │   N    │    message - VARCHAR            │
│    authorized - BOOLEAN         │        │    created_at - DATETIME        │
│    confidence - FLOAT           │        │    acknowledged - BOOLEAN       │
│    image_path - VARCHAR         │        │ 🔗 acknowledged_by (FK) - INT   │
│    notes - TEXT                 │        │    acknowledged_at - DATETIME   │
└─────────────┬───────────────────┘        └─────────────┬───────────────────┘
              │ N                                        │ N
              │                                          │
              │ 1                                        │ 1
              └──────────────────────────────────────────┘
                            USERS (acknowledged_by)
```

## 🔑 CLAVES PRIMARIAS:
- users.id (Autoincremental)
- vehicles.id (Autoincremental)  
- access_logs.id (Autoincremental)
- alerts.id (Autoincremental)

## 🔗 CLAVES FORÁNEAS:
- vehicles.user_id → users.id
- access_logs.user_id → users.id (NULL permitido)
- alerts.access_log_id → access_logs.id
- alerts.acknowledged_by → users.id (NULL permitido)

## 📋 CARDINALIDADES:
- users (1) ←→ (N) vehicles
- users (1) ←→ (N) access_logs  
- access_logs (1) ←→ (N) alerts
- users (1) ←→ (N) alerts (acknowledged_by)

## 🎯 TABLA PRINCIPAL PARA ANÁLISIS:
**ACCESS_LOGS** es la tabla más importante porque:
- Registra TODOS los eventos del sistema
- Conecta usuarios con sus accesos
- Genera métricas y reportes
- Base para alertas de seguridad

## 💡 PUNTOS CLAVE PARA TU CLASE:

### 1. INTEGRIDAD REFERENCIAL:
- Cascade DELETE en users → vehicles
- NULL permitido en access_logs.user_id (placas no registradas)

### 2. OPTIMIZACIÓN:
- Índices en columnas más consultadas (timestamp, plate_number)
- Índices compuestos para consultas específicas

### 3. ESCALABILIDAD:
- Función de limpieza automática (6 meses)
- Separación entre datos transaccionales (access_logs) y maestros (users/vehicles)

### 4. SEGURIDAD:
- Hashes para contraseñas
- Roles y permisos
- Auditoría completa de accesos

### 5. CASOS DE USO REALES:
- Control de acceso vehicular en universidades
- Estacionamientos corporativos
- Condominios residenciales
- Centros comerciales