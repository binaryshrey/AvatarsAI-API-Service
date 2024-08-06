from pydantic import BaseModel, Field


class User(BaseModel):
    user_id: str = Field(min_length=1, max_length=100, title='user ID')
    user_email: str = Field(min_length=7, max_length=100, title='user email ID')
    is_pro: bool

    # Default config override
    class Config:
        schema_extra = {
            'example': {
                'user_id': 'abc_xyz_123_890',
                'user_email': 'xyz@gmail.com',
                'is_pro': False
            }
        }


class Query(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    user_email: str = Field(min_length=1, max_length=100)
    is_pro_member: bool
    query_title: str = Field(min_length=1, max_length=1000)
    avatar_type: str = Field(min_length=1, max_length=100)
    query_language: str = Field(min_length=1, max_length=20)
    query_tone: str = Field(min_length=1, max_length=20)
    api_key: str = Field(min_length=0, max_length=200)
    model: str = Field(min_length=0, max_length=200)
    prompt: str = Field(min_length=0, max_length=1000)

    # Default config override
    class Config:
        schema_extra = {
            'example': {
                'user_id': 'abcd_wxyz',
                'user_email': 'abcd@gmail.com',
                'is_pro_member': False,
                'query_title': "What's the square root of 196?",
                'avatar_type': "Maths Teacher",
                'query_language': 'English',
                'query_tone': 'Convincing',
                'api_key': 'xxxx-1111-xxxx',
                'model': 'GPT - 3.5 Turbo (ChatGPT)',
                'prompt': "You're are an expert Maths Teacher. You're goal is answer following questions: "
            }
        }


class UserLevel(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    user_email: str = Field(min_length=1, max_length=100)

    # Default config override
    class Config:
        schema_extra = {
            'example': {
                'user_id': 'abcd_wxyz',
                'user_email': 'abcd@gmail.com',
            }
        }


class AvatarsList(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    user_email: str = Field(min_length=1, max_length=100)

    # Default config override
    class Config:
        schema_extra = {
            'example': {
                'user_id': 'abcd_wxyz',
                'user_email': 'abcd@gmail.com',
            }
        }

class Trending(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    user_email: str = Field(min_length=1, max_length=100)
    trending_query: str = Field(min_length=1, max_length=100)

    # Default config override
    class Config:
        schema_extra = {
            'example': {
                'user_id': 'abcd_wxyz',
                'user_email': 'abcd@gmail.com',
                'trending_query': 'sports',

            }
        }