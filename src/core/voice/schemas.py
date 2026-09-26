from enum import StrEnum

from pydantic import BaseModel, Field


class SupportedLanguages(StrEnum):
    ENGLISH = 'en'


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


class SupportedTone(StrEnum):
    NEUTRAL = 'neutral'
    CHEERFUL = 'cheerful'
    DRAMATIC = 'dramatic'
    CALM = 'calm'
    MYSTERIOUS = 'mysterious'
    STERN = 'stern'
    SARCASTIC = 'sarcastic'
    WHISPER = 'whisper'


class VoiceSettings(BaseModel):
    enabled:  bool               = Field(default=False)
    voice:    SupportedVoice     = Field(default=SupportedVoice.CORAL)
    tone:     SupportedTone      = Field(default=SupportedTone.NEUTRAL)
    language: SupportedLanguages = Field(default=SupportedLanguages.ENGLISH)


class VoiceOptions(BaseModel):
    voices:    list[SupportedVoice]     = Field(default_factory=lambda: list(SupportedVoice))
    tones:     list[SupportedTone]      = Field(default_factory=lambda: list(SupportedTone))
    languages: list[SupportedLanguages] = Field(default_factory=lambda: list(SupportedLanguages))


class SpeakRequest(BaseModel):
    text:     str               = Field(min_length=1, max_length=4000)
    voice:    SupportedVoice    = Field(default=SupportedVoice.CORAL)
    tone:     SupportedTone     = Field(default=SupportedTone.NEUTRAL)
    language: SupportedLanguages = Field(default=SupportedLanguages.ENGLISH)
