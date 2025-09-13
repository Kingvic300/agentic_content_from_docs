from configuration.configuration import Configuration as Config
from services.memory import AgentMemory


class BaseAgent:
    def __init__(self, name: str, config: Config, memory: AgentMemory):
        self.name = name
        self.config = config
        self.memory = memory
        self.status = "idle"

    def update_status(self, status: str):
        self.status = status