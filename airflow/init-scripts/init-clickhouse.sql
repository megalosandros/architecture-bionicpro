-- Инициализация ClickHouse для OLAP аналитики

-- Создание базы данных
CREATE DATABASE IF NOT EXISTS bionicpro_analytics;

-- Таблица агрегированной телеметрии
CREATE TABLE IF NOT EXISTS bionicpro_analytics.telemetry_aggregated
(
    user_id String,
    prosthesis_id String,
    date Date,
    hour UInt8,
    total_events UInt32,
    avg_battery_level Float32,
    min_battery_level UInt8,
    max_battery_level UInt8,
    avg_response_time_ms Float32,
    min_response_time_ms UInt32,
    max_response_time_ms UInt32,
    avg_signal_quality Float32,
    movement_counts Map(String, UInt32),
    error_counts Map(String, UInt32),
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (user_id, prosthesis_id, date, hour)
SETTINGS index_granularity = 8192;

-- Таблица витрины для отчетов (объединение CRM + Телеметрия)
CREATE TABLE IF NOT EXISTS bionicpro_analytics.customer_prosthesis_report
(
    -- Данные клиента из CRM
    customer_id String,
    first_name String,
    last_name String,
    email String,
    phone String,
    country_code String,
    registration_date DateTime,
    consent_data_processing UInt8,
    
    -- Данные заказа
    order_id String,
    order_date DateTime,
    total_amount Decimal(12, 2),
    order_status String,
    
    -- Данные протеза
    prosthesis_id String,
    prosthesis_type String,
    manufacture_date Date,
    delivery_date Nullable(Date),
    warranty_end_date Nullable(Date),
    prosthesis_status String,
    
    -- Агрегированная телеметрия за последние 30 дней
    telemetry_events_count UInt32,
    avg_battery_level Float32,
    avg_response_time_ms Float32,
    avg_signal_quality Float32,
    most_common_movement String,
    total_errors UInt32,
    last_telemetry_date Nullable(DateTime),
    
    -- Метаданные витрины
    report_generated_at DateTime DEFAULT now(),
    data_actual_as_of DateTime
)
ENGINE = ReplacingMergeTree(report_generated_at)
PARTITION BY toYYYYMM(order_date)
ORDER BY (customer_id, prosthesis_id)
SETTINGS index_granularity = 8192;

-- Таблица детальной телеметрии (реплика из PostgreSQL)
CREATE TABLE IF NOT EXISTS bionicpro_analytics.telemetry_detailed
(
    id UInt64,
    prosthesis_id String,
    user_id String,
    timestamp DateTime,
    sensor_data String,
    battery_level UInt8,
    movement_type String,
    response_time_ms UInt32,
    error_code String,
    signal_quality Float32,
    created_at DateTime
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (user_id, prosthesis_id, timestamp)
SETTINGS index_granularity = 8192;

-- Материализованное представление для автоматической агрегации
CREATE MATERIALIZED VIEW IF NOT EXISTS bionicpro_analytics.telemetry_aggregated_mv
TO bionicpro_analytics.telemetry_aggregated
AS
SELECT
    user_id,
    prosthesis_id,
    toDate(timestamp) as date,
    toHour(timestamp) as hour,
    count() as total_events,
    avg(battery_level) as avg_battery_level,
    min(battery_level) as min_battery_level,
    max(battery_level) as max_battery_level,
    avg(response_time_ms) as avg_response_time_ms,
    min(response_time_ms) as min_response_time_ms,
    max(response_time_ms) as max_response_time_ms,
    avg(signal_quality) as avg_signal_quality,
    sumMap(map(movement_type, 1)) as movement_counts,
    sumMap(map(error_code, 1)) as error_counts,
    now() as created_at
FROM bionicpro_analytics.telemetry_detailed
GROUP BY user_id, prosthesis_id, date, hour;

COMMENT ON TABLE bionicpro_analytics.telemetry_aggregated IS 'Агрегированная телеметрия по часам';
COMMENT ON TABLE bionicpro_analytics.customer_prosthesis_report IS 'Витрина данных для сервиса отчетов';
COMMENT ON TABLE bionicpro_analytics.telemetry_detailed IS 'Детальная телеметрия (реплика из PostgreSQL)';
