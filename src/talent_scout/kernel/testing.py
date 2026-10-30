from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from pydantic import Field


class FakeToolChatModel(GenericFakeChatModel):
    # Keeps the tools it was given so tests can check they survive a fallback.
    bound_tools: list = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        self.bound_tools = list(tools)
        return self
