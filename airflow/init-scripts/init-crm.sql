-- Инициализация CRM БД (имитация Oracle Database 12 на PostgreSQL)

-- Таблица клиентов
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(100) PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(200) UNIQUE,
    phone VARCHAR(50),
    country_code VARCHAR(10) DEFAULT 'RU',
    registration_date TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    consent_data_processing BOOLEAN DEFAULT false,
    consent_date TIMESTAMP
);

-- Таблица заказов
CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(100) PRIMARY KEY,
    customer_id VARCHAR(100) REFERENCES customers(customer_id),
    order_date TIMESTAMP DEFAULT NOW(),
    total_amount NUMERIC(12,2),
    currency VARCHAR(10) DEFAULT 'RUB',
    status VARCHAR(50) DEFAULT 'pending',
    payment_status VARCHAR(50) DEFAULT 'unpaid',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Таблица протезов (связь с заказами)
CREATE TABLE IF NOT EXISTS prosthesis_orders (
    prosthesis_order_id VARCHAR(100) PRIMARY KEY,
    order_id VARCHAR(100) REFERENCES orders(order_id),
    prosthesis_id VARCHAR(100) UNIQUE NOT NULL,
    prosthesis_type VARCHAR(100),
    manufacture_date DATE,
    delivery_date DATE,
    warranty_end_date DATE,
    status VARCHAR(50) DEFAULT 'in_production',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Таблица визитов и примерок
CREATE TABLE IF NOT EXISTS appointments (
    appointment_id VARCHAR(100) PRIMARY KEY,
    customer_id VARCHAR(100) REFERENCES customers(customer_id),
    prosthesis_order_id VARCHAR(100) REFERENCES prosthesis_orders(prosthesis_order_id),
    appointment_type VARCHAR(50), -- 'initial_measurement', 'fitting', 'training', 'adjustment'
    appointment_date TIMESTAMP,
    status VARCHAR(50) DEFAULT 'scheduled',
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_prosthesis_orders_order_id ON prosthesis_orders(order_id);
CREATE INDEX IF NOT EXISTS idx_prosthesis_orders_prosthesis_id ON prosthesis_orders(prosthesis_id);
CREATE INDEX IF NOT EXISTS idx_appointments_customer_id ON appointments(customer_id);

-- Вставка тестовых данных

-- Клиенты
INSERT INTO customers (customer_id, first_name, last_name, email, phone, country_code, registration_date, consent_data_processing, consent_date)
VALUES 
    ('USER-001', 'Иван', 'Петров', 'ivan.petrov@example.com', '+79991234567', 'RU', NOW() - INTERVAL '6 months', true, NOW() - INTERVAL '6 months'),
    ('USER-002', 'Мария', 'Сидорова', 'maria.sidorova@example.com', '+79997654321', 'RU', NOW() - INTERVAL '4 months', true, NOW() - INTERVAL '4 months'),
    ('USER-003', 'Алексей', 'Смирнов', 'alexey.smirnov@example.com', '+79995556677', 'RU', NOW() - INTERVAL '3 months', true, NOW() - INTERVAL '3 months'),
    ('USER-004', 'Елена', 'Васильева', 'elena.vasilyeva@example.com', '+79998887766', 'RU', NOW() - INTERVAL '2 months', false, NULL);

-- Заказы
INSERT INTO orders (order_id, customer_id, order_date, total_amount, status, payment_status)
VALUES 
    ('ORD-001', 'USER-001', NOW() - INTERVAL '5 months', 1500000.00, 'completed', 'paid'),
    ('ORD-002', 'USER-002', NOW() - INTERVAL '3 months', 1650000.00, 'completed', 'paid'),
    ('ORD-003', 'USER-003', NOW() - INTERVAL '2 months', 1800000.00, 'in_progress', 'paid'),
    ('ORD-004', 'USER-004', NOW() - INTERVAL '1 month', 1550000.00, 'pending', 'unpaid');

-- Протезы
INSERT INTO prosthesis_orders (prosthesis_order_id, order_id, prosthesis_id, prosthesis_type, manufacture_date, delivery_date, warranty_end_date, status)
VALUES 
    ('PORD-001', 'ORD-001', 'PROS-001', 'arm_prosthesis_advanced', NOW() - INTERVAL '4 months', NOW() - INTERVAL '3 months', NOW() + INTERVAL '2 years', 'delivered'),
    ('PORD-002', 'ORD-002', 'PROS-002', 'arm_prosthesis_premium', NOW() - INTERVAL '2 months', NOW() - INTERVAL '1 month', NOW() + INTERVAL '2 years', 'delivered'),
    ('PORD-003', 'ORD-003', 'PROS-003', 'arm_prosthesis_advanced', NOW() - INTERVAL '1 month', NULL, NULL, 'in_production');

-- Визиты
INSERT INTO appointments (appointment_id, customer_id, prosthesis_order_id, appointment_type, appointment_date, status, notes)
VALUES 
    ('APPT-001', 'USER-001', 'PORD-001', 'initial_measurement', NOW() - INTERVAL '5 months', 'completed', 'Первичный замер выполнен'),
    ('APPT-002', 'USER-001', 'PORD-001', 'fitting', NOW() - INTERVAL '4 months', 'completed', 'Примерка 1'),
    ('APPT-003', 'USER-001', 'PORD-001', 'training', NOW() - INTERVAL '3 months', 'completed', 'Обучение пользованию протезом'),
    ('APPT-004', 'USER-002', 'PORD-002', 'initial_measurement', NOW() - INTERVAL '3 months', 'completed', 'Первичный замер'),
    ('APPT-005', 'USER-002', 'PORD-002', 'training', NOW() - INTERVAL '1 month', 'completed', 'Обучение завершено'),
    ('APPT-006', 'USER-003', 'PORD-003', 'initial_measurement', NOW() - INTERVAL '2 months', 'completed', 'Замер выполнен'),
    ('APPT-007', 'USER-003', 'PORD-003', 'fitting', NOW() + INTERVAL '1 week', 'scheduled', 'Запланирована примерка');

COMMENT ON TABLE customers IS 'Клиенты BionicPRO';
COMMENT ON TABLE orders IS 'Заказы протезов';
COMMENT ON TABLE prosthesis_orders IS 'Информация о конкретных протезах в заказах';
COMMENT ON TABLE appointments IS 'История визитов и примерок';
