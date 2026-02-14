"""
BionicPRO Incremental Telemetry DAG
Инкрементальная загрузка телеметрии в режиме, близком к реальному времени
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import logging

# Настройки по умолчанию
default_args = {
    'owner': 'bionicpro-data-team',
    'depends_on_past': True,
    'start_date': datetime(2024, 12, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=2),
    'execution_timeout': timedelta(minutes=15),
}


def get_last_processed_id(**context):
    """
    Получение ID последней обработанной записи
    """
    from clickhouse_driver import Client
    
    client = Client(
        host='clickhouse',
        port=9000,
        database='bionicpro_analytics',
        user='clickhouse_user',
        password='clickhouse_password'
    )
    
    try:
        result = client.execute(
            'SELECT max(id) FROM telemetry_detailed'
        )
        last_id = result[0][0] if result and result[0][0] else 0
    except Exception as e:
        logging.warning(f"Не удалось получить последний ID: {e}")
        last_id = 0
    
    logging.info(f"Последний обработанный ID: {last_id}")
    
    context['task_instance'].xcom_push(key='last_id', value=last_id)
    
    return last_id


def extract_new_telemetry(**context):
    """
    Извлечение новой телеметрии с момента последней загрузки
    """
    last_id = context['task_instance'].xcom_pull(
        key='last_id',
        task_ids='get_last_processed_id'
    )
    
    if last_id is None:
        last_id = 0
    
    logging.info(f"Извлечение телеметрии с ID > {last_id}")
    
    pg_hook = PostgresHook(postgres_conn_id='postgres_main_conn')
    
    query = f"""
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
    WHERE id > {last_id}
    ORDER BY id ASC
    LIMIT 10000
    """
    
    new_data = pg_hook.get_records(query)
    
    logging.info(f"Найдено {len(new_data)} новых записей")
    
    context['task_instance'].xcom_push(key='new_telemetry', value=new_data)
    
    return len(new_data)


def load_incremental_telemetry(**context):
    """
    Инкрементальная загрузка новой телеметрии
    """
    from clickhouse_driver import Client
    
    new_data = context['task_instance'].xcom_pull(
        key='new_telemetry',
        task_ids='extract_new_telemetry'
    )
    
    if not new_data:
        logging.info("Нет новых данных для загрузки")
        return 0
    
    client = Client(
        host='clickhouse',
        port=9000,
        database='bionicpro_analytics',
        user='clickhouse_user',
        password='clickhouse_password'
    )
    
    # Подготовка данных
    data_to_insert = []
    for row in new_data:
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
    
    # Вставка данных
    client.execute(
        'INSERT INTO telemetry_detailed VALUES',
        data_to_insert
    )
    
    logging.info(f"Загружено {len(data_to_insert)} записей инкрементально")
    
    return len(data_to_insert)


def update_mart_incremental(**context):
    """
    Обновление витрины для пользователей с новой телеметрией
    """
    from clickhouse_driver import Client
    
    new_data = context['task_instance'].xcom_pull(
        key='new_telemetry',
        task_ids='extract_new_telemetry'
    )
    
    if not new_data:
        logging.info("Нет данных для обновления витрины")
        return 0
    
    # Получаем уникальные user_id из новых данных
    affected_users = set([row[2] for row in new_data])
    
    logging.info(f"Обновление витрины для {len(affected_users)} пользователей")
    
    client = Client(
        host='clickhouse',
        port=9000,
        database='bionicpro_analytics',
        user='clickhouse_user',
        password='clickhouse_password'
    )
    
    # Для каждого затронутого пользователя пересчитываем статистику
    for user_id in affected_users:
        # Получаем обновленную статистику
        update_query = f"""
        ALTER TABLE customer_prosthesis_report
        UPDATE 
            telemetry_events_count = (
                SELECT count() FROM telemetry_detailed 
                WHERE user_id = '{user_id}' 
                AND timestamp >= now() - INTERVAL 30 DAY
            ),
            avg_battery_level = (
                SELECT avg(battery_level) FROM telemetry_detailed 
                WHERE user_id = '{user_id}' 
                AND timestamp >= now() - INTERVAL 30 DAY
            ),
            avg_response_time_ms = (
                SELECT avg(response_time_ms) FROM telemetry_detailed 
                WHERE user_id = '{user_id}' 
                AND timestamp >= now() - INTERVAL 30 DAY
            ),
            avg_signal_quality = (
                SELECT avg(signal_quality) FROM telemetry_detailed 
                WHERE user_id = '{user_id}' 
                AND timestamp >= now() - INTERVAL 30 DAY
            ),
            last_telemetry_date = (
                SELECT max(timestamp) FROM telemetry_detailed 
                WHERE user_id = '{user_id}'
            ),
            data_actual_as_of = now()
        WHERE customer_id = '{user_id}'
        """
        
        try:
            client.execute(update_query)
        except Exception as e:
            logging.warning(f"Ошибка обновления для пользователя {user_id}: {e}")
    
    logging.info(f"Витрина обновлена для {len(affected_users)} пользователей")
    
    return len(affected_users)


# Определение DAG для инкрементальной загрузки
with DAG(
    'bionicpro_incremental_telemetry',
    default_args=default_args,
    description='Инкрементальная загрузка телеметрии каждые 15 минут',
    schedule_interval='*/15 * * * *',  # Каждые 15 минут
    catchup=False,
    tags=['bionicpro', 'incremental', 'telemetry', 'realtime'],
    max_active_runs=1,
) as dag:
    
    # Задача 1: Получить последний обработанный ID
    get_last_id_task = PythonOperator(
        task_id='get_last_processed_id',
        python_callable=get_last_processed_id,
        provide_context=True,
    )
    
    # Задача 2: Извлечь новые данные
    extract_new_task = PythonOperator(
        task_id='extract_new_telemetry',
        python_callable=extract_new_telemetry,
        provide_context=True,
    )
    
    # Задача 3: Загрузить новые данные
    load_incremental_task = PythonOperator(
        task_id='load_incremental_telemetry',
        python_callable=load_incremental_telemetry,
        provide_context=True,
    )
    
    # Задача 4: Обновить витрину
    update_mart_task = PythonOperator(
        task_id='update_mart_incremental',
        python_callable=update_mart_incremental,
        provide_context=True,
    )
    
    # Зависимости
    get_last_id_task >> extract_new_task >> load_incremental_task >> update_mart_task
