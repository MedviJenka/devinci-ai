import json
import requests
from core.settings import Config


NPC_SERVICE_URL = 'http://localhost:5555'


def generate_npc_response(npc_name: str, prompt: str) -> str:
    """Call the NPC service's streaming /talk endpoint and return the NPC's full reply."""
    url = f'{NPC_SERVICE_URL}/api/{Config.API_VERSION}/npcs/{npc_name}/talk'
    headers = {'Authorization': f'Bearer {Config.TEST_API_KEY}'}
    response = requests.get(url, params={'query': prompt}, headers=headers, stream=True, timeout=30)
    response.raise_for_status()

    chunks: list[str] = []
    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.startswith('data: '):
            continue
        event = json.loads(line[len('data: '):])
        if event['type'] == 'chunk':
            chunks.append(event['text'])
        elif event['type'] == 'done':
            return event['text']
        elif event['type'] == 'error':
            raise RuntimeError(event['message'])

    return ''.join(chunks)