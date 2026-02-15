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

-- Клиенты (customer_id = Keycloak User UUID)
INSERT INTO customers (customer_id, first_name, last_name, email, phone, country_code, registration_date, consent_data_processing, consent_date)
VALUES 
    ('1ebd24ab-87e6-40ce-a1bd-ded5aa9d205e', 'Иван', 'Петров', 'ivan.petrov@example.com', '+79991234567', 'RU', NOW() - INTERVAL '6 months', true, NOW() - INTERVAL '6 months'),
    ('61c813cd-2251-4a29-9415-57fec09a8c8f', 'Мария', 'Сидорова', 'maria.sidorova@example.com', '+79997654321', 'RU', NOW() - INTERVAL '4 months', true, NOW() - INTERVAL '4 months'),
    ('d0ec1834-b77d-4e3a-9ba5-1ce10ac6855c', 'Сергей', 'Протезов', 'sergey.p@example.com', '+79215556677', 'RU', NOW() - INTERVAL '3 months', true, NOW() - INTERVAL '3 months'),
    ('5fb8041c-4e30-41ea-bd32-d075859100b8', 'Елена', 'Тестова', 'elena.test@example.com', '+79328887766', 'RU', NOW() - INTERVAL '2 months', true, NOW() - INTERVAL '2 months'),
    ('043f5200-eab2-4d13-9c7e-01b84ba26d94', 'Дмитрий', 'Калибров', 'dmitry.k@example.com', '+79435554433', 'RU', NOW() - INTERVAL '1 month', true, NOW() - INTERVAL '1 month');

-- Заказы
INSERT INTO orders (order_id, customer_id, order_date, total_amount, status, payment_status)
VALUES 
    ('ORD-001', '1ebd24ab-87e6-40ce-a1bd-ded5aa9d205e', NOW() - INTERVAL '5 months', 1500000.00, 'completed', 'paid'),
    ('ORD-002', '61c813cd-2251-4a29-9415-57fec09a8c8f', NOW() - INTERVAL '3 months', 1650000.00, 'completed', 'paid'),
    ('ORD-003', 'd0ec1834-b77d-4e3a-9ba5-1ce10ac6855c', NOW() - INTERVAL '2 months', 1800000.00, 'in_progress', 'paid'),
    ('ORD-004', '5fb8041c-4e30-41ea-bd32-d075859100b8', NOW() - INTERVAL '1 month', 1550000.00, 'completed', 'paid'),
    ('ORD-005', '043f5200-eab2-4d13-9c7e-01b84ba26d94', NOW() - INTERVAL '20 days', 1700000.00, 'completed', 'paid');

-- Протезы
INSERT INTO prosthesis_orders (prosthesis_order_id, order_id, prosthesis_id, prosthesis_type, manufacture_date, delivery_date, warranty_end_date, status)
VALUES 
    ('PORD-001', 'ORD-001', 'PROS-001', 'arm_prosthesis_advanced', NOW() - INTERVAL '4 months', NOW() - INTERVAL '3 months', NOW() + INTERVAL '2 years', 'delivered'),
    ('PORD-002', 'ORD-002', 'PROS-002', 'arm_prosthesis_premium', NOW() - INTERVAL '2 months', NOW() - INTERVAL '1 month', NOW() + INTERVAL '2 years', 'delivered'),
    ('PORD-003', 'ORD-003', 'PROS-003', 'arm_prosthesis_advanced', NOW() - INTERVAL '1 month', NULL, NULL, 'in_production'),
    ('PORD-004', 'ORD-004', 'PROS-004', 'arm_prosthesis_premium', NOW() - INTERVAL '20 days', NOW() - INTERVAL '10 days', NOW() + INTERVAL '2 years', 'delivered'),
    ('PORD-005', 'ORD-005', 'PROS-005', 'leg_prosthesis_advanced', NOW() - INTERVAL '15 days', NOW() - INTERVAL '5 days', NOW() + INTERVAL '2 years', 'delivered');

-- Визиты
INSERT INTO appointments (appointment_id, customer_id, prosthesis_order_id, appointment_type, appointment_date, status, notes)
VALUES 
    ('APPT-001', '1ebd24ab-87e6-40ce-a1bd-ded5aa9d205e', 'PORD-001', 'initial_measurement', NOW() - INTERVAL '5 months', 'completed', 'Первичный замер выполнен'),
    ('APPT-002', '1ebd24ab-87e6-40ce-a1bd-ded5aa9d205e', 'PORD-001', 'fitting', NOW() - INTERVAL '4 months', 'completed', 'Примерка 1'),
    ('APPT-003', '1ebd24ab-87e6-40ce-a1bd-ded5aa9d205e', 'PORD-001', 'training', NOW() - INTERVAL '3 months', 'completed', 'Обучение пользованию протезом'),
    ('APPT-004', '61c813cd-2251-4a29-9415-57fec09a8c8f', 'PORD-002', 'initial_measurement', NOW() - INTERVAL '3 months', 'completed', 'Первичный замер'),
    ('APPT-005', '61c813cd-2251-4a29-9415-57fec09a8c8f', 'PORD-002', 'training', NOW() - INTERVAL '1 month', 'completed', 'Обучение завершено'),
    ('APPT-006', 'd0ec1834-b77d-4e3a-9ba5-1ce10ac6855c', 'PORD-003', 'initial_measurement', NOW() - INTERVAL '2 months', 'completed', 'Замер выполнен'),
    ('APPT-007', 'd0ec1834-b77d-4e3a-9ba5-1ce10ac6855c', 'PORD-003', 'fitting', NOW() + INTERVAL '1 week', 'scheduled', 'Запланирована примерка'),
    ('APPT-008', '5fb8041c-4e30-41ea-bd32-d075859100b8', 'PORD-004', 'initial_measurement', NOW() - INTERVAL '1 month', 'completed', 'Первичный замер'),
    ('APPT-009', '5fb8041c-4e30-41ea-bd32-d075859100b8', 'PORD-004', 'training', NOW() - INTERVAL '10 days', 'completed', 'Обучение завершено'),
    ('APPT-010', '043f5200-eab2-4d13-9c7e-01b84ba26d94', 'PORD-005', 'initial_measurement', NOW() - INTERVAL '20 days', 'completed', 'Первичный замер'),
    ('APPT-011', '043f5200-eab2-4d13-9c7e-01b84ba26d94', 'PORD-005', 'training', NOW() - INTERVAL '5 days', 'completed', 'Обучение завершено');

COMMENT ON TABLE customers IS 'Клиенты BionicPRO';
COMMENT ON TABLE orders IS 'Заказы протезов';
COMMENT ON TABLE prosthesis_orders IS 'Информация о конкретных протезах в заказах';
COMMENT ON TABLE appointments IS 'История визитов и примерок';