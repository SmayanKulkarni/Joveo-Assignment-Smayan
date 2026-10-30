# 05: Tiers.chat and check_balance

**What to build:** `fetch_agent`'s entry point: a tier call that takes a message history and tools and returns an `AIMessage`, with tools still bound after a fallback. Also the pre-Run balance check, which refuses to spend when the OpenRouter balance is below the floor. Spec: [Kernel LLD](../../../docs/lld/kernel.md) §12, §15.

Calling `check_balance` before a Run starts or resumes is the Run Controller's job, not this ticket's.

**Blocked by:** 04: Tiers.structured, end to end.

**Status:** done

- [x] `chat` binds tools to each model before `with_fallbacks`, and shares the transport retry, fallback, semaphore and tracing from ticket 04
- [x] `FakeToolChatModel` is a few-line `GenericFakeChatModel` subclass whose `bind_tools` returns itself
- [x] Test: `chat` returns an `AIMessage` with tool calls from the fake
- [x] Test: when the first model fails, the fallback model answers with its tools still bound
- [x] `check_balance(settings)` reads `GET /api/v1/key` and returns the balance
- [x] Test: with a mocked response, a balance below `balance_floor_usd` raises and one above it returns
- [x] Live smoke: `check_balance` returns a real number, and one `chat` call with a trivial tool on `minimax/minimax-m3.1-flash` returns a tool call
