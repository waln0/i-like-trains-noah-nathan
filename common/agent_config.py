from pydantic import BaseModel


class AgentConfig(BaseModel):
    nickname: str
    agent_file_name: str
