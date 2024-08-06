from datetime import datetime
from functools import wraps
from db.schemas import Query
from db.database import SessionLocal
from email.message import EmailMessage
from starlette.requests import Request
from slowapi.errors import RateLimitExceeded
import ssl, smtplib, random, logging, requests
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader, APIKeyQuery
from starlette.responses import JSONResponse, Response
from utils.configs import APP_API_KEY, QUERY_API_JWT_1, QUERY_API_JWT_2, QUERY_API_JWT_3, ALERT_SENDER, ALERT_RECEIVER, \
    ALERT_SERVER, ALERT_PORT, ALERT_KEY, PRO_CHECK_KEY, NEWS_API_KEY3, NEWS_API_KEY2, NEWS_API_KEY1
from utils.constants import LANGUAGES, TONES

api_key_query = APIKeyQuery(name="api-key", auto_error=False)
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

class CustomUnAuthException(HTTPException):
    def __init__(self, detail: str):
        self.detail = {
            'message': detail,
            'access_count': -1,
            'success': False
        }
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=self.detail
        )

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_api_key(query_key: str = Security(api_key_query),
                header_key: str = Security(api_key_header)):
    if query_key == APP_API_KEY:
        return query_key
    if header_key == APP_API_KEY:
        return header_key
    logging.warning("Invalid Request - Incorrect API Key!")
    raise CustomUnAuthException("Invalid Request! You seem to be on a stale app version, Kindly update the app for continued access!")


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    a simple JSON response that includes the details of the rate limit
    that was hit. If no limit is hit, the countdown is added to headers.
    """
    response = JSONResponse(
        {"message": 'Too many requests (Rate limit reached). Please try again in sometime.'}, status_code=200
    )
    response = request.app.state.limiter._inject_headers(response, request.state.view_rate_limit)
    return response


def get_user_agent(request: Request):
    return request.headers.get('user-agent')



def check_user_agent(func):
    @wraps(func)
    async def wrapper(request: Request, query: Query, *args, **kwargs):
        user_agent = get_user_agent(request)
        if 'okhttp' not in user_agent or query.user_id is None:
            client_address = f'{request.client.host}:{request.client.port}'
            send_alert(client_address, 'query', query.user_id, query.user_email)
            return {
                'message': f"Unauthorized access! Host IP with physical address || UserID : {query.user_id} || UserEmail : {query.user_email} recorded!"}
    return wrapper



def get_query_prompt(query):
    if query.query_title.startswith("LIVE:"):
        return query.query_title
    elif query.query_title == "Continue":
        return query.query_title
    return f'{query.prompt} in {query.query_language} language with {query.query_tone} tone - \n{query.query_title}'


def get_payload(prompt, query):
    # language = "English"
    # detected_language = detect(prompt)
    # logging.warning(prompt)
    # logging.warning(detected_language)
    # if detected_language in LANGUAGES_ABBR.keys():
    #     language = LANGUAGES_ABBR.get(detected_language)
    # else:
    #     language = "English"

    return {
        "operation": "chatExecute",
        "params": {
            "text": prompt,
            "languageId": LANGUAGES.get(query.query_language),
            "toneId": TONES.get(query.query_tone)
        }
    }


def get_query_key():
    random_key = random.choice([1, 2, 3])
    if random_key == 1:
        return f"{QUERY_API_JWT_1}"
    elif random_key == 2:
        return f"{QUERY_API_JWT_2}"
    else:
        return f"{QUERY_API_JWT_3}"


def get_headers(query_key):
    user_agent = 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Mobile Safari/537.36'
    random_key = random.choice([1, 2])
    if random_key == 1:
        user_agent = 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Mobile Safari/537.36'
    else:
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15'

    return {
        'Authentication': 'Bearer ' + query_key,
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-us',
        'Host': 'api.rytr.me',
        'Content-Type': 'application/json',
        'Origin': 'https://app.rytr.me',
        'Referer': 'https://app.rytr.me/',
        'User-Agent': user_agent

    }


def get_artist_uri():
    return 'https://aperture-sandy.vercel.app/generate'


def get_image_base_uri():
    return 'https://image.lexica.art/full_jpg/'


def get_artist_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36',
        'Origin': 'https://aperture-sandy.vercel.app',
        'Referer': 'https://aperture-sandy.vercel.app/',
        'Content-Type': 'application/json'
}


def get_pro_check_headers():
    return {'Authorization': f'Api-Key {PRO_CHECK_KEY}'}


def send_alert(client_address, route="", client_id="", client_email=""):
    subject = 'AvatarsAI API | Unauthorized Access Detected!'
    body = f""" Unauthorized access by user with 
                Host IP : {client_address} 
                UserId : {client_id}
                UserEmail : {client_email}
                detected at {datetime.now()}
                on route : {route}
            """

    em = EmailMessage()
    em['From'] = ALERT_SENDER
    em['To'] = ALERT_RECEIVER
    em['Subject'] = subject
    em.set_content(body)

    context = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL(ALERT_SERVER, ALERT_PORT, context=context) as smtp:
            smtp.login(ALERT_SENDER, ALERT_KEY)
            smtp.sendmail(ALERT_SENDER, ALERT_RECEIVER, em.as_string())
            logging.warning("Alert send!")
    except Exception as e:
        logging.warning(f'Exception error - Send alert: {str(e)}')




def get_trending_news_api_key():
    random_key = random.choice([1, 2, 3])
    if random_key == 1:
        return f"{NEWS_API_KEY1}"
    elif random_key == 2:
        return f"{NEWS_API_KEY2}"
    else:
        return f"{NEWS_API_KEY3}"


