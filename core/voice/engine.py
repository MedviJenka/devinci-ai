from collections.abc import AsyncGenerator
from openai import AsyncOpenAI
from core.voice.schemas import SupportedLanguages
from dataclasses import dataclass


NPC_INSTRUCTIONS = (
    'You are voicing a character in an interactive story. '
    'Speak fully in character, with pacing and emotion that match the tone of the line.'
)


@dataclass
class VoiceEngine:

    model: str = 'gpt-4o-mini-tts'
    voice: str = 'coral'
    instructions: str = NPC_INSTRUCTIONS

    async def stream_bytes(self, text: str, language: SupportedLanguages, openai_client: AsyncOpenAI) -> AsyncGenerator[bytes, None]:
        async with openai_client.audio.speech.with_streaming_response.create(
            model=self.model,
            voice=self.voice,
            input=text,
            instructions=self.instructions,
            response_format='mp3',
        ) as tts_response:
            async for audio_chunk in tts_response.iter_bytes(chunk_size=4096):
                yield audio_chunk
