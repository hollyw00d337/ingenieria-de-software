-- Crear base de datos
CREATE DATABASE plate_recognition_db;

-- Conectar a la base de datos
\c plate_recognition_db;

-- Crear extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Las tablas se crearán automáticamente con SQLAlchemy
-- Este script es solo para referencia de la estructura

-- Índices adicionales para optimización
CREATE INDEX IF NOT EXISTS idx_access_logs_timestamp ON access_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_access_logs_plate_date ON access_logs(plate_number, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_vehicles_active ON vehicles(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_users_occupation ON users(occupation) WHERE is_active = true;

-- Función para limpiar registros antiguos (ejecutar como tarea programada)
CREATE OR REPLACE FUNCTION cleanup_old_access_logs()
RETURNS void AS $$
BEGIN
    DELETE FROM access_logs 
    WHERE timestamp < NOW() - INTERVAL '6 months';
END;
$$ LANGUAGE plpgsql;
