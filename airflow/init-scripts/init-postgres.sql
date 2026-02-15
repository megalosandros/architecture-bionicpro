-- Инициализация основной БД PostgreSQL для телеметрии
-- Таблица телеметрии с протезов

CREATE TABLE IF NOT EXISTS prosthesis_telemetry (
    id BIGSERIAL PRIMARY KEY,
    prosthesis_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    sensor_data JSONB,
    battery_level INTEGER CHECK (battery_level >= 0 AND battery_level <= 100),
    movement_type VARCHAR(50),
    response_time_ms INTEGER,
    error_code VARCHAR(20),
    signal_quality NUMERIC(5,2) CHECK (signal_quality >= 0 AND signal_quality <= 100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_telemetry_user_id ON prosthesis_telemetry(user_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_prosthesis_id ON prosthesis_telemetry(prosthesis_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON prosthesis_telemetry(timestamp);
CREATE INDEX IF NOT EXISTS idx_telemetry_user_timestamp ON prosthesis_telemetry(user_id, timestamp);

-- Таблица для хранения моделей ML
CREATE TABLE IF NOT EXISTS ml_models (
    id BIGSERIAL PRIMARY KEY,
    model_name VARCHAR(200) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    model_data BYTEA,
    accuracy NUMERIC(5,4),
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT false,
    UNIQUE(model_name, model_version)
);

-- Вставка тестовых данных телеметрии
INSERT INTO prosthesis_telemetry 
    (prosthesis_id, user_id, timestamp, sensor_data, battery_level, movement_type, response_time_ms, signal_quality)
VALUES 
    ('PROS-001', 'USER-001', NOW() - INTERVAL '1 hour', '{"sensor1": 0.75, "sensor2": 0.82}', 85, 'grip', 95, 92.5),
    ('PROS-001', 'USER-001', NOW() - INTERVAL '50 minutes', '{"sensor1": 0.78, "sensor2": 0.80}', 84, 'release', 98, 91.2),
    ('PROS-002', 'USER-002', NOW() - INTERVAL '2 hours', '{"sensor1": 0.65, "sensor2": 0.70}', 90, 'grip', 102, 88.5),
    ('PROS-002', 'USER-002', NOW() - INTERVAL '1 hour 30 minutes', '{"sensor1": 0.68, "sensor2": 0.72}', 89, 'pinch', 97, 89.3),
    ('PROS-003', 'USER-003', NOW() - INTERVAL '3 hours', '{"sensor1": 0.80, "sensor2": 0.85}', 75, 'grip', 93, 94.1);

COMMENT ON TABLE prosthesis_telemetry IS 'Телеметрия с протезов в режиме реального времени';
COMMENT ON TABLE ml_models IS 'Хранилище ML моделей для распознавания движений';
