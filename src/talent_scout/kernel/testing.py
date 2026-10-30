from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.runnables import Runnable
from langchain_typesafe import ClassifierResponse, NoulAnswer
from pydantic import Field


class FakeToolChatModel(GenericFakeChatModel):
    # Keeps the tools it was given so tests can check they survive a fallback.
    bound_tools: list = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        self.bound_tools = list(tools)
        return self


class FakeClassifier(Runnable):
    """Stands in for TypeSafeClassifier: canned p_yes per question id, after raising any queued errors."""

    def __init__(self, answers: dict[str, float], model: str, errors: list[Exception]):
        self.answers, self.model, self.errors, self.calls = answers, model, list(errors), []

    def invoke(self, input, config=None, **kwargs):
        self.calls.append(input)
        if self.errors:
            raise self.errors.pop(0)
        return ClassifierResponse(
            model=self.model,
            answers={q: NoulAnswer(type="noul", noul=self.answers[q]) for q in input["questions"]},
        )

    async def ainvoke(self, input, config=None, **kwargs):
        return self.invoke(input, config)


def fake_classifier(answers: dict[str, float], *, model: str = "typesafe/jev-1.14-20260101", errors=()) -> FakeClassifier:
    return FakeClassifier(answers, model, list(errors))
