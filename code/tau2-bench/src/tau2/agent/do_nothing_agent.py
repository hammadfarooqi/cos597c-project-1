"""A trivial baseline agent that takes no actions.

The agent never calls a tool and ends the conversation on its first turn.
Its score shows how many tasks pass when the environment stays unchanged
and the agent communicates nothing.
"""

from typing import Optional

from tau2.agent.base_agent import HalfDuplexAgent, ValidAgentInputMessage
from tau2.data_model.message import AssistantMessage, Message
from tau2.environment.toolkit import Tool


class DoNothingAgent(HalfDuplexAgent[None]):
    """Agent that immediately stops without calling tools or helping the user."""

    STOP_TOKEN = "###STOP###"

    def __init__(self, tools: list[Tool], domain_policy: str):
        super().__init__(tools=tools, domain_policy=domain_policy)

    def get_init_state(self, message_history: Optional[list[Message]] = None) -> None:
        return None

    def generate_next_message(
        self, message: ValidAgentInputMessage, state: None
    ) -> tuple[AssistantMessage, None]:
        return AssistantMessage(role="assistant", content=self.STOP_TOKEN), state

    @classmethod
    def is_stop(cls, message: AssistantMessage) -> bool:
        return message.content is not None and cls.STOP_TOKEN in message.content


def create_do_nothing_agent(tools, domain_policy, **kwargs):
    """Factory function for DoNothingAgent. Ignores LLM arguments."""
    return DoNothingAgent(tools=tools, domain_policy=domain_policy)
