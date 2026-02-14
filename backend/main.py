"""
BionicPRO Reports API Backend
Обеспечивает доступ к отчетам из ClickHouse с Row-Level Security
"""
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import jwt
from jwt import PyJWKClient
import clickhouse_connect
import logging
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BionicPRO Reports API",
    description="API для получения отчетов о работе протезов",
    version="1.0.0"
)

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://frontend:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Конфигурация из переменных окружения
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
CLICKHOUSE_DATABASE = os.getenv("CLICKHOUSE_DATABASE", "bionicpro_analytics")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "reports-realm")
JWKS_URL = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"

# ClickHouse клиент
try:
    ch_client = clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        database=CLICKHOUSE_DATABASE,
        username=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD
    )
    logger.info(f"Connected to ClickHouse at {CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}")
except Exception as e:
    logger.error(f"Failed to connect to ClickHouse: {e}")
    ch_client = None


# Модели данных
class ProsthesisReport(BaseModel):
    """Отчет о работе протеза"""
    customer_id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    country_code: str
    
    order_id: str
    order_date: datetime
    total_amount: float
    order_status: str
    
    prosthesis_id: str
    prosthesis_type: str
    manufacture_date: datetime
    delivery_date: Optional[datetime]
    warranty_end_date: Optional[datetime]
    prosthesis_status: str
    
    telemetry_events_count: int
    avg_battery_level: Optional[float]
    avg_response_time_ms: Optional[float]
    avg_signal_quality: Optional[float]
    most_common_movement: Optional[str]
    total_errors: int
    last_telemetry_date: Optional[datetime]
    
    report_generated_at: datetime
    data_actual_as_of: datetime


class UserInfo(BaseModel):
    """Информация о пользователе из JWT токена"""
    customer_id: str
    preferred_username: str
    email: Optional[str]


# Функции аутентификации и авторизации
def verify_token(token: str) -> dict:
    """
    Проверяет JWT токен от Keycloak и возвращает payload
    """
    try:
        jwks_client = PyJWKClient(JWKS_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={
                "verify_signature": True,
                "verify_aud": False,  # Audience может быть разным
                "verify_iss": False,  # Issuer проверяется через JWKS URL
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
            }
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(status_code=401, detail="Token verification failed")


def get_current_user(authorization: str = Header(...)) -> UserInfo:
    """
    Извлекает информацию о текущем пользователе из JWT токена
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, 
            detail="Invalid Authorization header format. Expected 'Bearer <token>'"
        )
    
    token = authorization[7:]  # Убираем "Bearer "
    payload = verify_token(token)
    
    # Извлекаем customer_id из токена
    # В реальном проекте это может быть custom claim
    preferred_username = payload.get("preferred_username")
    if not preferred_username:
        raise HTTPException(
            status_code=403, 
            detail="Token does not contain preferred_username claim"
        )
    
    # Маппинг username -> customer_id (в реальной системе это должно быть в БД)
    # Для демонстрации используем username как customer_id
    customer_id = payload.get("sub")  # subject - уникальный ID пользователя
    
    return UserInfo(
        customer_id=customer_id,
        preferred_username=preferred_username,
        email=payload.get("email")
    )


# API эндпоинты
@app.get("/health")
def health_check():
    """Проверка здоровья сервиса"""
    clickhouse_status = "ok" if ch_client else "unavailable"
    return {
        "status": "ok",
        "clickhouse": clickhouse_status,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/reports", response_model=List[ProsthesisReport])
async def get_reports(
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Получить отчеты о протезах для текущего пользователя.
    
    Применяется Row-Level Security:
    - Пользователь видит только свои протезы
    - Фильтрация происходит на уровне SQL запроса
    """
    if not ch_client:
        raise HTTPException(
            status_code=503, 
            detail="ClickHouse connection unavailable"
        )
    
    # RLS: Фильтрация по customer_id пользователя
    query = """
        SELECT 
            customer_id,
            first_name,
            last_name,
            email,
            phone,
            country_code,
            
            order_id,
            order_date,
            total_amount,
            order_status,
            
            prosthesis_id,
            prosthesis_type,
            manufacture_date,
            delivery_date,
            warranty_end_date,
            prosthesis_status,
            
            telemetry_events_count,
            avg_battery_level,
            avg_response_time_ms,
            avg_signal_quality,
            most_common_movement,
            total_errors,
            last_telemetry_date,
            
            report_generated_at,
            data_actual_as_of
        FROM {database}.customer_prosthesis_report
        WHERE customer_id = %(customer_id)s
        ORDER BY order_date DESC, prosthesis_id
    """.format(database=CLICKHOUSE_DATABASE)
    
    try:
        logger.info(f"Fetching reports for customer_id: {current_user.customer_id}")
        
        result = ch_client.query(
            query, 
            parameters={"customer_id": current_user.customer_id}
        )
        
        reports = []
        for row in result.result_rows:
            reports.append(ProsthesisReport(
                customer_id=row[0],
                first_name=row[1],
                last_name=row[2],
                email=row[3],
                phone=row[4],
                country_code=row[5],
                
                order_id=row[6],
                order_date=row[7],
                total_amount=float(row[8]),
                order_status=row[9],
                
                prosthesis_id=row[10],
                prosthesis_type=row[11],
                manufacture_date=row[12],
                delivery_date=row[13],
                warranty_end_date=row[14],
                prosthesis_status=row[15],
                
                telemetry_events_count=row[16],
                avg_battery_level=row[17],
                avg_response_time_ms=row[18],
                avg_signal_quality=row[19],
                most_common_movement=row[20],
                total_errors=row[21],
                last_telemetry_date=row[22],
                
                report_generated_at=row[23],
                data_actual_as_of=row[24]
            ))
        
        logger.info(f"Found {len(reports)} reports for customer {current_user.customer_id}")
        return reports
        
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch reports: {str(e)}"
        )


@app.get("/reports/summary")
async def get_reports_summary(
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Получить сводную статистику по протезам пользователя
    """
    if not ch_client:
        raise HTTPException(
            status_code=503, 
            detail="ClickHouse connection unavailable"
        )
    
    query = """
        SELECT 
            count() as total_prostheses,
            countIf(prosthesis_status = 'active') as active_prostheses,
            sum(telemetry_events_count) as total_events,
            avg(avg_battery_level) as avg_battery,
            avg(avg_response_time_ms) as avg_response_time,
            sum(total_errors) as total_errors
        FROM {database}.customer_prosthesis_report
        WHERE customer_id = %(customer_id)s
    """.format(database=CLICKHOUSE_DATABASE)
    
    try:
        result = ch_client.query(
            query, 
            parameters={"customer_id": current_user.customer_id}
        )
        
        if result.result_rows:
            row = result.result_rows[0]
            return {
                "customer_id": current_user.customer_id,
                "total_prostheses": row[0],
                "active_prostheses": row[1],
                "total_events": row[2],
                "avg_battery_level": row[3],
                "avg_response_time_ms": row[4],
                "total_errors": row[5]
            }
        else:
            return {
                "customer_id": current_user.customer_id,
                "total_prostheses": 0,
                "active_prostheses": 0,
                "total_events": 0,
                "avg_battery_level": None,
                "avg_response_time_ms": None,
                "total_errors": 0
            }
            
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch summary: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    