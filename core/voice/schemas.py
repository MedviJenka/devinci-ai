from enum import StrEnum

from pydantic import BaseModel, Field


class SupportedLanguages(StrEnum):
    ENGLISH = 'en'
    HEBREW = 'he'


class SupportedVoice(StrEnum):
    ALLOY = 'alloy'
    ASH = 'ash'
    BALLAD = 'ballad'
    CORAL = 'coral'
    ECHO = 'echo'
    FABLE = 'fable'
    NOVA = 'nova'
    ONYX = 'onyx'
    SAGE = 'sage'
    SHIMMER = 'shimmer'
    VERSE = 'verse'


class VoiceSettings(BaseModel):
    enabled:  bool               = Field(default=False)
    voice:    SupportedVoice     = Field(default=SupportedVoice.CORAL)
    language: SupportedLanguages = Field(default=SupportedLanguages.ENGLISH)


class VoiceOptions(BaseModel):
    voices:    list[SupportedVoice]     = Field(default_factory=lambda: list(SupportedVoice))
    languages: list[SupportedLanguages] = Field(default_factory=lambda: list(SupportedLanguages))


class SpeakRequest(BaseModel):
    text:     str               = Field(min_length=1, max_length=4000)
    voice:    SupportedVoice    = Field(default=SupportedVoice.CORAL)
    language: SupportedLanguages = Field(default=SupportedLanguages.ENGLISH)
