from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings
from typing import Optional
from supabase import create_client


class Settings(BaseSettings):
    model_config                                = ConfigDict(extra='allow')
    API_VERSION:                  str           = Field(default='v1')
    ENV:                          str           = Field(default='dev')
    LOG_DIR:                      str           = Field(default='/logs')
    LOG_LEVEL:                    str           = Field(default='INFO')
    VERBOSE:                      bool          = Field(default=True)
    LOGFIRE_TOKEN:                Optional[str] = Field(default='')
    GHCR_TOKEN:                   str           = Field(default='')
    OPENAI_API_KEY:               str           = Field(default='')
    OPENAI_MODEL:                 str           = Field(default='')
    SUPABASE_PUBLISHABLE_API_KEY: str           = Field(default='')
    SUPABASE_SECRET_API_KEY:      str           = Field(default='')
    GOOGLE_OAUTH_CALLBACK_URI:    str           = Field(default='')
    SUPABASE_URL:                 str           = Field(default='')


Config = Settings()

db = create_client(supabase_url=Config.SUPABASE_URL, supabase_key=Config.SUPABASE_SECRET_API_KEY)
