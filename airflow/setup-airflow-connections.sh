#!/bin/bash

# =========================================================================
# BionicPRO - Скрипт настройки Airflow подключений
# =========================================================================

set -e

echo "================================="
echo "Настройка подключений Airflow"
echo "================================="
echo ""

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Проверяем, запущен ли Airflow
echo -e "${YELLOW}Проверка доступности Airflow...${NC}"
if ! docker compose ps | grep -q "airflow_webserver"; then
    echo -e "${RED}✗ Airflow webserver не запущен${NC}"
    echo "Сначала запустите сервисы: docker compose up -d"
    exit 1
fi

echo -e "${GREEN}✓ Airflow webserver запущен${NC}"
echo ""

# Функция для создания подключения
create_connection() {
    local conn_id=$1
    local conn_type=$2
    local host=$3
    local schema=$4
    local login=$5
    local password=$6
    local port=$7
    
    echo -e "${YELLOW}Создание подключения: $conn_id${NC}"
    
    # Удаляем существующее подключение (игнорируем ошибки)
    docker compose exec -T airflow_webserver airflow connections delete "$conn_id" 2>/dev/null || true
    
    # Создаем новое подключение
    if docker compose exec -T airflow_webserver airflow connections add "$conn_id" \
        --conn-type "$conn_type" \
        --conn-host "$host" \
        --conn-schema "$schema" \
        --conn-login "$login" \
        --conn-password "$password" \
        --conn-port "$port"; then
        echo -e "${GREEN}✓ Подключение $conn_id создано${NC}"
    else
        echo -e "${RED}✗ Ошибка создания подключения $conn_id${NC}"
        return 1
    fi
    echo ""
}

echo "Создание подключений к базам данных..."
echo ""

# Подключение к CRM БД
create_connection \
    "crm_db_conn" \
    "postgres" \
    "crm_db" \
    "crm_db" \
    "crm_user" \
    "crm_password" \
    "5432"

# Подключение к основной БД PostgreSQL (телеметрия)
create_connection \
    "postgres_main_conn" \
    "postgres" \
    "postgres_main" \
    "bionicpro_main" \
    "bionicpro_user" \
    "bionicpro_password" \
    "5432"

# Проверка созданных подключений
echo "================================="
echo -e "${GREEN}Проверка созданных подключений${NC}"
echo "================================="
echo ""

if docker compose exec -T airflow_webserver airflow connections list | grep -E "(crm_db_conn|postgres_main_conn)"; then
    echo ""
    echo -e "${GREEN}✓ Все подключения успешно созданы!${NC}"
else
    echo ""
    echo -e "${RED}✗ Не все подключения были созданы${NC}"
    exit 1
fi

echo ""
echo "================================="
echo -e "${GREEN}Настройка завершена успешно!${NC}"
echo "================================="
echo ""
echo "Следующие шаги:"
echo "1. Откройте Airflow UI: http://localhost:8081"
echo "2. Войдите (admin/admin)"
echo "3. Проверьте подключения: Admin -> Connections"
echo "4. Активируйте DAGs в главном меню"
echo ""