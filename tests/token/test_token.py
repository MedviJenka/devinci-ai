from fastapi.testclient import TestClient
from services.npc_service import app


client = TestClient(app)


def test_list_npcs_requires_auth(test_token):
    response = client.get(url="/api/v1/npcs/", headers={"Authorization": f"Bearer {test_token}"})
    print(f'\n{test_token}')
    assert response.status_code == 200
