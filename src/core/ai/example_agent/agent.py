from crewai import Agent
from crewai import Memory
from pydantic import BaseModel, Field
from dataclasses import dataclass
from core.useful.log import Logger
from typing import Generic, TypeVar, Optional, Type, Literal


T = TypeVar('T', bound=BaseModel)

log = Logger(name='{agent_name}-agent')

memory = Memory(storage='./memory')


@dataclass
class AgentFactory(Generic[T]):

    model: Optional[Type[BaseModel]] = None

    def run(self, prompt: str) -> str | dict:

        agent = Agent(role=f"npc agent", goal="npc agent", backstory='npc agent', verbose=False, memory=True, skills=['./skills'])

        if self.model:
            response = agent.kickoff(prompt, response_format=self.model).pydantic.model_dump()
            log.fire.info(f'agent response {response}')
            memory.remember(response)
            return response

        response = agent.kickoff(prompt).raw
        log.fire.info(f'agent response: {response}')
        memory.remember(response)
        return response


# example what use can do with schemas
class Schema(BaseModel):
    response:    str                             = Field(..., description='agent response')
    agent_mood:  Literal['calm', 'angry', 'sad'] = Field(..., description='agent mood')
    trust_level: float                           = Field(..., description='agent trust', ge=0, le=100)


agent = AgentFactory()
print(agent.run('how did u lose ur finger?'))
