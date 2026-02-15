"""
BionicPRO ETL DAG
Извлечение данных из CRM и PostgreSQL, загрузка в ClickHouse,
подготовка витрины для сервиса отчетов
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import logging
import json

# Настройки по умолчанию
default_args = {
    'owner': 'bionicpro-data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 12, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=1),
}


def extract_crm_data(**context):
    """
    Извлечение данных из CRM базы данных
    """
    logging.info("Начало извлечения данных из CRM...")
    
    crm_hook = PostgresHook(postgres_conn_id='crm_db_conn')
    
    # Запрос для извлечения данных клиентов, заказов и протезов
    query = """
    SELECT 
        c.customer_id,
        c.first_name,
        c.last_name,
        c.email,
        c.phone,
        c.country_code,
        c.registration_date,
        c.consent_data_processing,
        o.order_id,
        o.order_date,
        o.total_amount,
        o.status as order_status,
        po.prosthesis_id,
        po.prosthesis_type,
        po.manufacture_date,
        po.delivery_date,
        po.warranty_end_date,
        po.status as prosthesis_status
    FROM customers c
    LEFT JOIN orders o ON c.customer_id = o.customer_id
    LEFT JOIN prosthesis_orders po ON o.order_id = po.order_id
    WHERE c.is_active = true
        AND c.consent_data_processing = true
    ORDER BY c.customer_id, o.order_date DESC
    """
    
    crm_data = crm_hook.get_records(query)
    
    logging.info(f"Извлечено {len(crm_data)} записей из CRM")
    
    # Сохраняем данные в XCom для передачи следующим задачам
    context['task_instance'].xcom_push(key='crm_data', value=crm_data)
    
    return len(crm_data)


def extract_telemetry_data(**context):
    """
    Извлечение телеметрии из PostgreSQL
    """
    logging.info("Начало извлечения телеметрии...")
    
    pg_hook = PostgresHook(postgres_conn_id='postgres_main_conn')
    
    # Извлекаем телеметрию за последние 30 дней
    query = """
    SELECT 
        id,
        prosthesis_id,
        user_id,
        timestamp,
        sensor_data::text as sensor_data,
        battery_level,
        movement_type,
        response_time_ms,
        COALESCE(error_code, '') as error_code,
        signal_quality,
        created_at
    FROM prosthesis_telemetry
    WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
    ORDER BY timestamp DESC
    """
    
    telemetry_data = pg_hook.get_records(query)
    
    logging.info(f"Извлечено {len(telemetry_data)} записей телеметрии")
    
    context['task_instance'].xcom_push(key='telemetry_data', value=telemetry_data)
    
    return len(telemetry_data)


def load_telemetry_to_clickhouse(**context):
    """
    Загрузка телеметрии в ClickHouse
    """
    from clickhouse_driver import Client
    
    logging.info("Начало загрузки телеметрии в ClickHouse...")
    
    # Получаем данные из XCom
    telemetry_data = context['task_instance'].xcom_pull(
        key='telemetry_data', 
        task_ids='extract_telemetry_data'
    )
    
    if not telemetry_data:
        logging.warning("Нет данных телеметрии для загрузки")
        return 0
    
    # Подключение к ClickHouse
    client = Client(
        host='clickhouse',
        port=9000,
        database='bionicpro_analytics',
        user='clickhouse_user',
        password='clickhouse_password'
    )
    
    # Очистка старых данных (опционально, для обновления)
    # client.execute('TRUNCATE TABLE telemetry_detailed')
    
    # Подготовка данных для вставки
    data_to_insert = []
    for row in telemetry_data:
        data_to_insert.append({
            'id': row[0],
            'prosthesis_id': row[1],
            'user_id': row[2],
            'timestamp': row[3],
            'sensor_data': row[4],
            'battery_level': row[5] if row[5] is not None else 0,
            'movement_type': row[6] if row[6] else '',
            'response_time_ms': row[7] if row[7] is not None else 0,
            'error_code': row[8] if row[8] else '',
            'signal_quality': float(row[9]) if row[9] is not None else 0.0,
            'created_at': row[10]
        })
    
    # Массовая вставка
    client.execute(
        'INSERT INTO telemetry_detailed VALUES',
        data_to_insert
    )
    
    logging.info(f"Загружено {len(data_to_insert)} записей в ClickHouse")
    
    return len(data_to_insert)


def prepare_data_mart(**context):
    """
    Подготовка витрины данных с объединением CRM и телеметрии
    """
    from clickhouse_driver import Client
    
    logging.info("Начало подготовки витрины данных...")
    
    # Получаем данные из XCom
    crm_data = context['task_instance'].xcom_pull(
        key='crm_data',
        task_ids='extract_crm_data'
    )
    
    if not crm_data:
        logging.warning("Нет данных CRM для витрины")
        return 0
    
    # Подключение к ClickHouse
    client = Client(
        host='clickhouse',
        port=9000,
        database='bionicpro_analytics',
        user='clickhouse_user',
        password='clickhouse_password'
    )
    
    # Для каждого клиента и протеза агрегируем телеметрию
    mart_data = []
    
    for crm_row in crm_data:
        customer_id = crm_row[0]
        prosthesis_id = crm_row[12]
        
        if not prosthesis_id:
            continue
        
        # Получаем агрегированную телеметрию для этого протеза
        telemetry_stats = client.execute(f"""
            SELECT 
                count() as events_count,
                avg(battery_level) as avg_battery,
                avg(response_time_ms) as avg_response_time,
                avg(signal_quality) as avg_signal_quality,
                topK(1)(movement_type)[1] as most_common_movement,
                countIf(error_code != '') as total_errors,
                max(timestamp) as last_telemetry
            FROM telemetry_detailed
            WHERE user_id = '{customer_id}'
                AND prosthesis_id = '{prosthesis_id}'
                AND timestamp >= now() - INTERVAL 30 DAY
        """)
        
        if telemetry_stats and telemetry_stats[0][0] > 0:
            stats = telemetry_stats[0]
        else:
            stats = (0, 0, 0, 0, '', 0, None)
        
        # Формируем запись для витрины
        mart_record = {
            'customer_id': crm_row[0],
            'first_name': crm_row[1],
            'last_name': crm_row[2],
            'email': crm_row[3],
            'phone': crm_row[4],
            'country_code': crm_row[5],
            'registration_date': crm_row[6],
            'consent_data_processing': 1 if crm_row[7] else 0,
            'order_id': crm_row[8] if crm_row[8] else '',
            'order_date': crm_row[9] if crm_row[9] else datetime.now(),
            'total_amount': float(crm_row[10]) if crm_row[10] else 0.0,
            'order_status': crm_row[11] if crm_row[11] else '',
            'prosthesis_id': prosthesis_id,
            'prosthesis_type': crm_row[13] if crm_row[13] else '',
            'manufacture_date': crm_row[14] if crm_row[14] else datetime.now().date(),
            'delivery_date': crm_row[15],
            'warranty_end_date': crm_row[16],
            'prosthesis_status': crm_row[17] if crm_row[17] else '',
            'telemetry_events_count': stats[0],
            'avg_battery_level': float(stats[1]) if stats[1] else 0.0,
            'avg_response_time_ms': float(stats[2]) if stats[2] else 0.0,
            'avg_signal_quality': float(stats[3]) if stats[3] else 0.0,
            'most_common_movement': stats[4] if stats[4] else '',
            'total_errors': stats[5],
            'last_telemetry_date': stats[6],
            'report_generated_at': datetime.now(),
            'data_actual_as_of': datetime.now()
        }
        
        mart_data.append(mart_record)
    
    # Очистка старых данных витрины
    client.execute('TRUNCATE TABLE customer_prosthesis_report')
    
    # Загрузка новых данных
    if mart_data:
        client.execute(
            'INSERT INTO customer_prosthesis_report VALUES',
            mart_data
        )
    
    logging.info(f"Витрина данных подготовлена: {len(mart_data)} записей")
    
    return len(mart_data)


def validate_data_mart(**context):
    """
    Валидация витрины данных
    """
    from clickhouse_driver import Client
    
    logging.info("Валидация витрины данных...")
    
    client = Client(
        host='clickhouse',
        port=9000,
        database='bionicpro_analytics',
        user='clickhouse_user',
        password='clickhouse_password'
    )
    
    # Проверка количества записей
    count_result = client.execute(
        'SELECT count() FROM customer_prosthesis_report'
    )
    total_records = count_result[0][0]
    
    # Проверка актуальности данных
    freshness_check = client.execute("""
        SELECT 
            min(data_actual_as_of) as oldest_update,
            max(data_actual_as_of) as newest_update
        FROM customer_prosthesis_report
    """)
    
    logging.info(f"Всего записей в витрине: {total_records}")
    if freshness_check and freshness_check[0]:
        logging.info(f"Актуальность данных: {freshness_check[0][0]} - {freshness_check[0][1]}")
    
    # Проверка на дубликаты
    duplicates_check = client.execute("""
        SELECT customer_id, prosthesis_id, count() as cnt
        FROM customer_prosthesis_report
        GROUP BY customer_id, prosthesis_id
        HAVING cnt > 1
    """)
    
    if duplicates_check:
        logging.warning(f"Обнаружено {len(duplicates_check)} дубликатов!")
    else:
        logging.info("Дубликаты не обнаружены")
    
    return {
        'total_records': total_records,
        'has_duplicates': len(duplicates_check) > 0
    }


# Определение DAG
with DAG(
    'bionicpro_etl_pipeline',
    default_args=default_args,
    description='ETL процесс для BionicPRO: CRM -> ClickHouse + подготовка витрины',
    schedule_interval='0 2 * * *',  # Запуск каждый день в 2:00 UTC
    catchup=False,
    tags=['bionicpro', 'etl', 'crm', 'analytics'],
    max_active_runs=1,
) as dag:
    
    # Задача 1: Извлечение данных из CRM
    extract_crm_task = PythonOperator(
        task_id='extract_crm_data',
        python_callable=extract_crm_data,
        provide_context=True,
    )
    
    # Задача 2: Извлечение телеметрии
    extract_telemetry_task = PythonOperator(
        task_id='extract_telemetry_data',
        python_callable=extract_telemetry_data,
        provide_context=True,
    )
    
    # Задача 3: Загрузка телеметрии в ClickHouse
    load_telemetry_task = PythonOperator(
        task_id='load_telemetry_to_clickhouse',
        python_callable=load_telemetry_to_clickhouse,
        provide_context=True,
    )
    
    # Задача 4: Подготовка витрины данных
    prepare_mart_task = PythonOperator(
        task_id='prepare_data_mart',
        python_callable=prepare_data_mart,
        provide_context=True,
    )
    
    # Задача 5: Валидация витрины
    validate_mart_task = PythonOperator(
        task_id='validate_data_mart',
        python_callable=validate_data_mart,
        provide_context=True,
    )
    
    # Определение зависимостей задач
    # Сначала извлекаем данные параллельно
    [extract_crm_task, extract_telemetry_task] >> load_telemetry_task
    
    # Затем готовим витрину (требуются и CRM данные, и телеметрия)
    [extract_crm_task, load_telemetry_task] >> prepare_mart_task
    
    # И валидируем результат
    prepare_mart_task >> validate_mart_task