import asyncio
from collections.abc import Awaitable, Callable
from typing import Literal, TypeVar

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatResult
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_openrouter import ChatOpenRouter
from openrouter.errors import (
    BadGatewayResponseError,
    EdgeNetworkTimeoutResponseError,
    InternalServerResponseError,
    NoResponseError,
    PaymentRequiredResponseError,
    ProviderOverloadedResponseError,
    RequestTimeoutResponseError,
    ServiceUnavailableResponseError,
    TooManyRequestsResponseError,
)
from pydantic import BaseModel, ValidationError

from talent_scout.kernel.settings import Settings

Tier = Literal["cheap", "strong"]
M = TypeVar("M", bound=BaseModel)

MIN_MAX_TOKENS = 1000
TIMEOUT_MS = 60_000
KEY_URL = "https://openrouter.ai/api/v1/key"

# Failures of the provider, not of our request: retry, then try the next model.
_TRANSIENT = (
    TooManyRequestsResponseError,
    InternalServerResponseError,
    BadGatewayResponseError,
    ServiceUnavailableResponseError,
    EdgeNetworkTimeoutResponseError,
    RequestTimeoutResponseError,
    ProviderOverloadedResponseError,
    NoResponseError,
    httpx.TransportError,
)
# 402 is usually in-flight spend that clears, so it is retried, but the next model shares the account.
_RETRY_ON = _TRANSIENT + (PaymentRequiredResponseError,)

# Tests switch this off so retries don't sleep.
_BACKOFF = True


class LLMExhausted(Exception):
    def __init__(self, tier: str, name: str, attempts: int):
        super().__init__(f"{tier} chain for '{name}' exhausted after {attempts} attempts")
        self.tier, self.name, self.attempts = tier, name, attempts


class BalanceTooLow(Exception):
    pass


class _BadOutput(Exception):
    """A model returned content that failed validation twice, feedback retry included."""

    def __init__(self, attempts: int):
        super().__init__("model output failed validation")
        self.attempts = attempts


_FALLBACK_ON = _TRANSIENT + (_BadOutput,)


class _CostedOpenRouter(ChatOpenRouter):
    """ChatOpenRouter whose messages carry OpenRouter's cost in usage_metadata, where LangSmith reads it."""

    def _create_chat_result(self, response) -> ChatResult:
        result = super()._create_chat_result(response)
        for gen in result.generations:
            msg = gen.message
            cost = msg.response_metadata.get("cost")
            if isinstance(msg, AIMessage) and msg.usage_metadata and cost is not None:
                msg.usage_metadata = {**msg.usage_metadata, "total_cost": cost}
        return result


def _response_format(schema: type[BaseModel]) -> dict:
    fn = convert_to_openai_tool(schema, strict=True)["function"]
    return {"type": "json_schema", "json_schema": {"name": fn["name"], "schema": fn["parameters"], "strict": True}}


class Tiers:
    def __init__(self, chains: dict[Tier, list[BaseChatModel]], settings: Settings):
        self._chains = chains
        self._settings = settings
        self._sem = asyncio.Semaphore(settings.llm_concurrency)

    def structured(
        self, tier: Tier, schema: type[M], *, system: str, name: str, max_tokens: int | None = None
    ) -> Runnable[str, M]:
        steps = self._steps(tier, max_tokens, response_format=_response_format(schema))

        def per_model(call: Runnable) -> Callable[[str, RunnableConfig], Awaitable[M]]:
            async def run(text: str, config: RunnableConfig) -> M:
                messages: list[BaseMessage] = [SystemMessage(system), HumanMessage(text)]
                last: ValidationError | None = None
                for _ in range(2):
                    reply = await call.ainvoke(messages, config)
                    try:
                        return schema.model_validate_json(reply.text)
                    except ValidationError as err:
                        last = err
                        # Resend with the bad output and the error so the model can correct itself.
                        messages = [
                            *messages,
                            AIMessage(reply.text),
                            HumanMessage(f"That failed validation:\n{err}\nReturn corrected JSON."),
                        ]
                raise _BadOutput(attempts=2) from last

            return run

        return self._driver(tier, name, [per_model(s) for s in steps])

    def chat(
        self, tier: Tier, *, tools: list[BaseTool], name: str, max_tokens: int | None = None
    ) -> Runnable[list[AnyMessage], AIMessage]:
        # Tools go on each model before the chain, since a fallback wrapper has no bind_tools.
        steps = self._steps(tier, max_tokens, tools=tools)

        def per_model(call: Runnable):
            async def run(messages: list[AnyMessage], config: RunnableConfig) -> AIMessage:
                return await call.ainvoke(messages, config)

            return run

        return self._driver(tier, name, [per_model(s) for s in steps])

    def _steps(self, tier: Tier, max_tokens: int | None, *, tools=None, **bind) -> list[Runnable]:
        limit = getattr(self._settings, f"max_tokens_{tier}") if max_tokens is None else max_tokens
        if limit < MIN_MAX_TOKENS:
            raise ValueError(f"max_tokens must be at least {MIN_MAX_TOKENS}, got {limit}")
        steps = []
        for m in self._chains[tier]:
            model_id = getattr(m, "model_name", type(m).__name__)
            bound = (m.bind_tools(tools) if tools else m).bind(max_tokens=limit, **bind)
            # Tag before wrapping: with_config on the wrapper would only name the outer chain.
            bound = bound.with_config(tags=[f"tier:{tier}", f"model:{model_id}"])
            steps.append(self._guarded(bound))
        return steps

    def _guarded(self, model: Runnable) -> Runnable:
        async def call(messages, config: RunnableConfig):
            # The slot is held per attempt, not across backoff sleeps.
            async with self._sem:
                return await model.ainvoke(messages, config)

        return RunnableLambda(call).with_retry(
            retry_if_exception_type=_RETRY_ON, wait_exponential_jitter=_BACKOFF, stop_after_attempt=3
        )

    def _driver(self, tier: Tier, name: str, steps: list[Callable]) -> Runnable:
        async def run(arg, config: RunnableConfig):
            attempts, last = 0, None
            for step in steps:
                try:
                    return await step(arg, config)
                except _FALLBACK_ON as err:
                    attempts += getattr(err, "attempts", 1)
                    last = err
            raise LLMExhausted(tier, name, attempts) from last

        return RunnableLambda(run).with_config(
            run_name=f"llm:{name}", metadata={"tier": tier, "name": name}
        )


def make_tiers(settings: Settings) -> Tiers:
    def build(ids: list[str], effort: str) -> list[BaseChatModel]:
        return [
            _CostedOpenRouter(
                model=i,
                api_key=settings.openrouter_api_key,
                reasoning={"effort": effort},
                openrouter_provider={"require_parameters": True},
                timeout=TIMEOUT_MS,
                max_retries=0,  # our with_retry owns retries
            )
            for i in ids
        ]

    return Tiers(
        {
            "cheap": build(settings.llm_cheap, settings.reasoning_cheap),
            "strong": build(settings.llm_strong, settings.reasoning_strong),
        },
        settings,
    )


async def check_balance(settings: Settings) -> float:
    async with httpx.AsyncClient(timeout=TIMEOUT_MS / 1000) as client:
        r = await client.get(KEY_URL, headers={"Authorization": f"Bearer {settings.openrouter_api_key}"})
    r.raise_for_status()
    left = r.json()["data"]["limit_remaining"]
    # A key with no spend limit reports null; nothing on the key can run out.
    balance = float("inf") if left is None else float(left)
    if balance < settings.balance_floor_usd:
        raise BalanceTooLow(f"OpenRouter balance ${balance:.2f} is below the ${settings.balance_floor_usd:.2f} floor")
    return balance
