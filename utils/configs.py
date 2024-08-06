import os
from dotenv import load_dotenv


load_dotenv()


def env_get(env_var: str) -> str:
    val = os.environ.get(env_var)
    if not val:
        raise KeyError(f"Env variable '{env_var}' is not set!")
    return val


DB_HOST = env_get("DB_HOST")
DB_NAME = env_get("DB_NAME")
DB_PASSWORD = env_get("DB_PASSWORD")
DB_USERNAME = env_get("DB_USERNAME")
REDIS_HOST = env_get("REDISHOST")
REDIS_PASSWORD = env_get("REDISPASSWORD")
REDIS_PORT = env_get("REDISPORT")
REDIS_URL = env_get("REDIS_URL")
REDIS_USER = env_get("REDISUSER")
PROMPTS_LIMIT = env_get("PROMPTS_LIMIT")
FREE_PROMPTS_LIMIT = env_get("FREE_PROMPTS_LIMIT")
QUERY_API = env_get("QUERY_API")
QUERY_API_JWT_1 = env_get("QUERY_API_JWT_1")
QUERY_API_JWT_2 = env_get("QUERY_API_JWT_2")
QUERY_API_JWT_3 = env_get("QUERY_API_JWT_3")
APP_API_KEY = env_get("APP_API_KEY")
DAILY_LIMIT = env_get("DAILY_LIMIT")
ALERT_SENDER = env_get("ALERT_SENDER")
ALERT_RECEIVER = env_get("ALERT_RECEIVER")
ALERT_KEY = env_get("ALERT_KEY")
ALERT_SERVER = env_get("ALERT_SERVER")
ALERT_PORT = env_get("ALERT_PORT")
PRO_CHECK_URI = env_get("PRO_CHECK_URI")
PRO_CHECK_KEY = env_get("PRO_CHECK_KEY")
NEWS_API_KEY1 = env_get("NEWS_API_KEY1")
NEWS_API_KEY2 = env_get("NEWS_API_KEY2")
NEWS_API_KEY3 = env_get("NEWS_API_KEY3")
GEMINI_API = env_get("GEMINI_API")



