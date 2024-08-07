########################################################################### - Imports - ###########################################################################
from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from db import models
from slowapi import Limiter
from db.database import engine
from sqlalchemy.orm import Session
import google.generativeai as genai
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
import requests, logging, aioredis, json, openai
from db.schemas import Query, UserLevel, AvatarsList, Trending
from utils.constants import AVATARS_LIST, CATEGORIES_LIST, BANNED_ACCOUNTS, TRENDING_QUERY_MAPPING
from fastapi import FastAPI, Depends, Security, Request
from utils.configs import REDIS_URL, FREE_PROMPTS_LIMIT, PROMPTS_LIMIT, DAILY_LIMIT, PRO_CHECK_URI, GEMINI_API
from utils.utility import get_api_key, get_db, rate_limit_exceeded_handler, get_payload, \
    get_query_prompt, get_query_key, CustomUnAuthException, get_pro_check_headers, \
    get_trending_news_api_key, get_artist_uri, get_artist_headers, get_image_base_uri, check_user_agent

########################################################################### - Imports - ###########################################################################




# SETUP LOGGER
# logging.basicConfig(encoding='utf-8', level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__file__)




# DNA
app = FastAPI(
    title='AvatarsAI APP-v2',
    description='AvatarsAI API',
    version='0.2.0',
    docs_url='/v2000/documentation',
    redoc_url='/v2000/redoc',
    openapi_url='/v2000/openapi.json'
)




# INIT
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
models.Base.metadata.create_all(bind=engine)




# On-Start
@app.on_event("startup")
async def startup_event():
    # connect to Redis on startup
    app.state.redis = await aioredis.create_redis_pool(f"{REDIS_URL}")
    logger.info("Connected to Redis")




# On-Destroy
@app.on_event("shutdown")
async def shutdown_event():
    # disconnect from Redis on shutdown
    app.state.redis.close()
    await app.state.redis.wait_closed()
    logger.info("Disconnected from Redis")




# CustomUnAuthException
@app.exception_handler(CustomUnAuthException)
async def custom_exception_handler(request, exc):
    return JSONResponse(content=exc.detail)




# root
@app.get('/')
@limiter.limit("2/minute")
async def root(request: Request):
    return {'message': 'root'}



# health
@app.get('/health')
@limiter.limit("2/minute")
async def check_alive(request: Request):
    return {'message': 'alive'}




# query
@app.post('/v2/query')
@check_user_agent
@limiter.limit("9/minute")
async def avatars_chat_query(request: Request, query: Query, api_key: str = Security(get_api_key), db: Session = Depends(get_db)):

    # banned acc filter
    if query.user_email in BANNED_ACCOUNTS:
        logger.warning(f"Banned Account - {query.user_email}")
        return {'message': f"You're PERMANENTLY BANNED and have been served a Cease & Desist Letter for Unauthorized Access to Avatars AI. Any further access will lead to LEGAL ACTIONS!", 'access_count': -1, 'success': False}




    # redis user-level rate-limit
    redis_key = f"counter:users/{query.user_email}"
    if await app.state.redis.exists(redis_key):
        count = await app.state.redis.incr(redis_key)
    else:
        count = await app.state.redis.set(redis_key, 1)
        await app.state.redis.expire(redis_key, 24*60*60)
    if count > int(DAILY_LIMIT) and query.api_key == '':
        logger.warning(f"user - {query.user_email} exceeded daily quota!")
        return {'message': 'Too many requests (Daily quota reached). \n\nPlease try again tomorrow or continue with your own OpenAI API key (generated from : https://platform.openai.com/account/api-keys )', 'access_count': -1, 'success': False}




    # get query prompt
    prompt = get_query_prompt(query)




    # get user from DB
    should_update_access_count = True
    db_user = db.query(models.UserEntity).filter(models.UserEntity.user_id == query.user_id).first()




    # check user pro access
    is_user_pro_member = False
    try:
        pro_headers = get_pro_check_headers()
        uri = f"{PRO_CHECK_URI}{query.user_id}/"
        response = requests.get(uri, headers=pro_headers).json()

        if response.get("data") is not None:
            if response.get("data").get("paid_access_levels") is not None:
                is_user_pro_member = response.get("data").get("paid_access_levels").get("premium").get("is_active")
            else:
                is_user_pro_member = False
        # else:
        #     client_address = f'{request.client.host}:{request.client.port}'
        #     send_alert(client_address, 'query', query.user_id, query.user_email)
        #     logger.warning(f"Unauthorized access! Host IP - {client_address} || UserID : {query.user_id} || UserEmail : {query.user_email} with physical address recorded!")
        #     return {'message': f"Unauthorized access! Host IP with physical address recorded!", 'access_count': -1, 'success': False}

    except Exception as e:
        logger.warning(f"Failed to get subscription status for user : {query.user_id} - {str(e)}")
        is_user_pro_member = False

    # if query.user_email == 'playconsole.shreyansh@gmail.com':
    #     is_user_pro_member = True


    # create new record if no user
    if not db_user:
        should_update_access_count = False
        new_user = models.UserEntity()
        new_user.user_id = query.user_id
        new_user.user_email = query.user_email
        new_user.is_pro = is_user_pro_member
        new_user.access_count = 1
        db.add(new_user)
        db.commit()
        logger.info(f"new user record created for - {query.user_email}")




    # else check access count and respond acc 
    else:
        user_access_count = db_user.access_count
        if not is_user_pro_member and user_access_count >= int(FREE_PROMPTS_LIMIT) and query.api_key == '':
            logger.warning(f"user - {query.user_email} exceeded free quota!")
            return {'message': "You have exhausted your FREE quota towards 'AVATARS AI - Chat Companion'.\n\n  Please subscribe to 'AVATARS AI - PRO' or add your own OpenAI API key (generated from : https://platform.openai.com/account/api-keys ) for continued access !", 'access_count': user_access_count, 'success': False}
        if user_access_count >= int(PROMPTS_LIMIT) and query.api_key == '':
            logger.warning(f"user - {query.user_email} exceeded total quota!")
            return {'message': 'Too many requests (Rate limit reached).\n  Please try again in sometime or add your own OpenAI API key (generated from : https://platform.openai.com/account/api-keys ) for continued access !', 'access_count': -1, 'success': False}




    try:
        # query IMAGE-GEN
        if query.avatar_type == 'Artist':
            logger.warning(f"Artist - userEmail: {query.user_email} - userId: {query.user_id} - prompt: {query.query_title}")
            artist_images = []
            try:
                req = requests.post(get_artist_uri(), json={"query": query.query_title}, headers=get_artist_headers())
                images = req.json()
                image_results = images[:5]
                for image in image_results:
                    image_uri = get_image_base_uri() + image
                    artist_images.append(image_uri)

                if should_update_access_count:
                    db_user.access_count = db_user.access_count + 1
                    db.add(db_user)
                    db.commit()
                    return {'message': artist_images, 'access_count': 1 if not db_user else db_user.access_count, 'success': True}
                return {'message': artist_images, 'access_count': 1 if not db_user else db_user.access_count, 'success': True}


            except Exception as e:
                logger.warning(f'IMAGE-GEN - Exception error: {str(e)}')
                return {'message': [], 'access_count': -1, 'success': False}



        # query
        elif prompt.startswith("LIVE:") or (query.api_key == '' and query.model == 'GPT - 3.5 Turbo (ChatGPT)') or query.model == 'Bard AI':
            logger.warning(f"query - userEmail: {query.user_email} - userId: {query.user_id} - prompt: {prompt}")

            try:
                genai.configure(api_key=GEMINI_API)
                generation_config = {
                    "temperature": 1,
                    "top_p": 0.95,
                    "top_k": 64,
                    "max_output_tokens": 8192,
                }

                model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    generation_config=generation_config,
                )

                chat_session = model.start_chat(history=[])
                res = chat_session.send_message(query.query_title)

                if res is not None:
                    if should_update_access_count:
                        db_user.access_count = db_user.access_count + 1
                        db.add(db_user)
                        db.commit()
                        return {'message': res.text, 'access_count': 1 if not db_user else db_user.access_count, 'success': True}
                    return {'message': res.text, 'access_count': 1 if not db_user else db_user.access_count, 'success': True}
                else:
                    return {'message': "AI is experiencing high server load, Please try again in 30 mins!", 'access_count': -1, 'success': False}


            except Exception as e:
                logger.warning(f'GEMINI AI - Exception error: {str(e)}')
                return {'message': "AI is experiencing high server load, Please try again in 30 mins!", 'access_count': -1, 'success': False}



        # query OPENAI-API
        else:
            logger.warning(f"OPENAI - userEmail: {query.user_email} - userId: {query.user_id} - prompt: {prompt} - API_KEY: {query.api_key} - Model: {query.model}")


            try:
                model = 'gpt-3.5-turbo'
                if query.model == 'GPT - 3.5 Turbo (ChatGPT)':
                    model = 'gpt-3.5-turbo'
                elif query.model == 'GPT - 3 (davinci)':
                    model = 'gpt-3.5-turbo'
                elif query.model == 'GPT - 4':
                    model = 'gpt-4'

                openai.api_key = query.api_key
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}]
                )
                data = response.choices
                if data is not None:
                    open_ai_response = data[0].message.content
                    open_ai_response_value = {'message': open_ai_response, 'access_count': 1 if not db_user else db_user.access_count, 'success': True}

                    if should_update_access_count:
                        db_user.access_count = db_user.access_count + 1
                        db.add(db_user)
                        db.commit()
                        return open_ai_response_value
                    return open_ai_response_value

                else:
                    logger.warning(f'No data : {str(data)}')
                    return {'message': f'No response received from OpenAI! {str(data)}', 'access_count': -1, 'success': False}

            except Exception as e:
                logger.warning(f'OpenAI - Exception error: {str(e)}')
                return {'message': f'{str(e)} <br/><br/>Alternatively select ChatGPT model and remove your provided API key from the chat settings and click apply', 'access_count': -1, 'success': False}


    except Exception as e:
        logger.warning(f'Exception error: {str(e)}')
    return {'message': 'Too many requests (Rate limit reached). Please try again in sometime!', 'access_count': -1, 'success': False}




# all app-categories-and-avatars
@app.post('/v2/avatars')
@limiter.limit("50/minute")
async def get_avatars(request: Request, avatarsList: AvatarsList, api_key: str = Security(get_api_key)):

    logger.warning(f"AVATARS - userEmail: {avatarsList.user_email} - userId: {avatarsList.user_id}")
    return {'categories': CATEGORIES_LIST, 'avatars': AVATARS_LIST}




# user access level
@app.post('/v2/level')
@limiter.limit("50/minute")
async def get_user_access_level(request: Request, userLevel: UserLevel, api_key: str = Security(get_api_key), db: Session = Depends(get_db)):


    logger.warning(f"LEVEL - userEmail: {userLevel.user_email} -  userId: {userLevel.user_id}")
    db_user = db.query(models.UserEntity).filter(models.UserEntity.user_email == userLevel.user_email).first()
    if not db_user:
        return {"access_count": 0}
    return {"access_count": db_user.access_count}




# trending news
@app.post('/v2/trending')
@limiter.limit("50/minute")
async def get_trending_news(request: Request, trending: Trending, api_key: str = Security(get_api_key)):


    logger.warning(f"TRENDING - userEmail: {trending.user_email} - userId: {trending.user_id}")
    trending_news_keyword_search = TRENDING_QUERY_MAPPING.get(trending.trending_query)


    # check redis cache
    if await app.state.redis.exists(f"{trending_news_keyword_search}"):
        cached_data = await app.state.redis.get(f"{trending_news_keyword_search}")
        if cached_data is not None:
            logger.warning("cache-hit")
            trending_cache = json.loads(cached_data).get("trending")
            return {'trending': trending_cache}
        else:
            logger.warning("cache-miss")
    


    try:
        trending_news_api_key = get_trending_news_api_key()
        trending_request = (f'https://newsapi.org/v2/everything?q={trending_news_keyword_search}&sortBy=publishedAt&apiKey={trending_news_api_key}&language=en')
        response = requests.get(trending_request).json()
        response_articles = []

        if response is not None:
            if response.get("articles") is not None:
                response_articles = response.get('articles')
                await app.state.redis.set(f"{trending_news_keyword_search}", json.dumps({'trending': response_articles}))
                await app.state.redis.expire(f"{trending_news_keyword_search}", 24 * 60 * 60 * 3)

        return {'trending': response_articles[:20]}

    except Exception as e:
        logger.warning(f'TRENDING - Exception error: {str(e)}')
        return {'trending': []}

