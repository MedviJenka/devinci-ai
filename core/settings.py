from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    model_config                                = ConfigDict(extra='allow')
    API_VERSION:                  str           = Field(default='v1')
    ENV:                          str           = Field(default='dev')
    LOG_DIR:                      str           = Field(default='/logs')
    LOG_LEVEL:                    str           = Field(default='INFO')
    VERBOSE:                      bool          = Field(default=True)
    LOGFIRE_TOKEN:                Optional[str] = Field(default=None)
    GHCR_TOKEN:                   str           = Field(...)
    OPENAI_API_KEY:               str           = Field(...)
    OPENAI_MODEL:                 str           = Field(default=None)
    SUPABASE_PUBLISHABLE_API_KEY: str           = Field(default=None)
    SUPABASE_SECRET_API_KEY:      str           = Field(default=None)
    GOOGLE_OAUTH_CALLBACK_URI:    str           = Field(default=None)


Config = Settings()
