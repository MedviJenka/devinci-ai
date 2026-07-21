from core.database.users.schemas import Subscription, UserSchema
from core.settings import db
from dataclasses import dataclass


@dataclass
class Users:

    def __post_init__(self) -> None:
        self.db = db

    def get(self, user_id: str) -> UserSchema | None:
        response = self.db.table('users').select('*').eq('id', user_id).maybe_single().execute()
        return UserSchema(**response.data) if response and response.data else None

    def create(self, user_id: str) -> UserSchema:
        response = self.db.table('users').insert({'id': user_id}).execute()
        return UserSchema(**response.data[0])

    def get_or_create(self, user_id: str) -> UserSchema:
        return self.get(user_id) or self.create(user_id)

    def update_to_paid(self, user_id: str, subscription: Subscription = 'Pro') -> UserSchema:
        response = self.db.table('users').update({'subscription': subscription}).eq('id', user_id).execute()
        return UserSchema(**response.data[0])

    def increment_api_calls(self, user_id: str) -> UserSchema:
        user = self.get_or_create(user_id)
        response = self.db.table('users').update({'api_calls': user.api_calls + 1}).eq('id', user_id).execute()
        return UserSchema(**response.data[0])

    def set_characters(self, user_id: str, characters: int) -> UserSchema:
        response = self.db.table('users').update({'characters': characters}).eq('id', user_id).execute()
        return UserSchema(**response.data[0])
