from collections.abc import AsyncGenerator
from openai import AsyncOpenAI
from core.voice.schemas import SupportedTone
from dataclasses import dataclass


NPC_INSTRUCTIONS = (
    'You are voicing a character in an interactive story. '
    'Speak fully in character, with pacing and emotion that match the tone of the line.'
)

TONE_INSTRUCTIONS: dict[SupportedTone, str] = {
    SupportedTone.NEUTRAL: '',
    SupportedTone.CHEERFUL: 'Sound upbeat, warm, and cheerful.',
    SupportedTone.DRAMATIC: 'Sound theatrical and dramatic, with heightened emotion and pacing.',
    SupportedTone.CALM: 'Sound calm, slow, and reassuring.',
    SupportedTone.MYSTERIOUS: 'Sound hushed, mysterious, and enigmatic.',
    SupportedTone.STERN: 'Sound stern, commanding, and serious.',
    SupportedTone.SARCASTIC: 'Sound dry and sarcastic.',
    SupportedTone.WHISPER: 'Speak in a hushed whisper, close and intimate.',
}


@dataclass
class VoiceEngine:

    model: str = 'gpt-4o-mini-tts'
    voice: str = 'alloy'
    tone: SupportedTone = SupportedTone.NEUTRAL

    @property
    def instructions(self) -> str:
        return f'{NPC_INSTRUCTIONS} {TONE_INSTRUCTIONS.get(self.tone, "")}'.strip()

    async def stream_bytes(self, text: str, openai_client: AsyncOpenAI, language='en') -> AsyncGenerator[bytes, None]:
        async with openai_client.audio.speech.with_streaming_response.create(
            model=self.model,
            voice=self.voice,
            input=text,
            instructions=self.instructions,
            response_format='mp3',
            speed=1.5
        ) as tts_response:
            async for audio_chunk in tts_response.iter_bytes(chunk_size=4096):
                yield audio_chunk


if __name__ == '__main__':

    import asyncio
    from core.settings import Config

    async def main() -> None:

        client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        voice = VoiceEngine()

        with open('voice_test_output.mp3', 'wb') as f:
            async for chunk in voice.stream_bytes(NPC_INSTRUCTIONS, client):
                f.write(chunk)

    asyncio.run(main())
