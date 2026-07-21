from core.settings import Config
from dataclasses import dataclass
from logfire import Logfire, configure


@dataclass
class Logger:

    name: str

    @property
    def fire(self) -> Logfire:
        return configure(service_name=self.name, token=Config.LOGFIRE_TOKEN, send_to_logfire='if-token-present')
