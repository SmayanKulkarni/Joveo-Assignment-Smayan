---
name: langchain-router
description: Routing table for the LangChain / LangGraph / Deep Agents / LangSmith skills installed in this project. Use this FIRST whenever a task involves building, scaffolding, debugging, deploying, or evaluating an agent with LangChain, LangGraph, Deep Agents, Managed Deep Agents, RAG, checkpointers, middleware, human-in-the-loop, langgraph CLI, parallel subagent fan-out, or agent evals - even if the user never names a skill. Tells you exactly which sibling skill(s) to load, and which to NOT load.
---

# LangChain skill router

Pick skills by matching the task to the table below. Load only the skills the task needs; each one is large. Do not guess from memory: these frameworks change fast, so the skills (and the live docs they point to) are the source of truth.

## Step 1: always start here for new agent work

If the project is new, or the user has not chosen a framework yet, load `ecosystem-primer` first. It decides LangChain vs LangGraph vs Deep Agents vs hybrid. Skip it only when the framework is already fixed and the task is a narrow edit.

For new projects or any install/version question, also load `langchain-dependencies`.

## Step 2: route by task

| Task | Load |
|---|---|
| Quick local scaffold, LangChain, Python | `langchain-python-quickstart` |
| Quick local scaffold, LangChain, TypeScript | `langchain-typescript-quickstart` |
| Quick local scaffold, LangGraph, Python | `langgraph-python-quickstart` |
| Quick local scaffold, LangGraph, TypeScript | `langgraph-typescript-quickstart` |
| Quick local scaffold, Deep Agent, Python | `deepagents-python-quickstart` |
| Quick local scaffold, Deep Agent, TypeScript | `deepagents-typescript-quickstart` |
| Write LangChain agent code: `create_agent`, `@tool`, tools | `langchain-fundamentals` |
| Approval of tool calls, custom middleware, structured output (Pydantic/Zod) | `langchain-middleware` |
| RAG: loaders, splitters, embeddings, vector stores | `langchain-rag` |
| Write any LangGraph code: StateGraph, nodes, edges, Command, Send, streaming | `langgraph-fundamentals` |
| Pause/resume, `interrupt()`, approval flows, error-handling tiers in LangGraph | `langgraph-human-in-the-loop` |
| Checkpointers, `thread_id`, time travel, Store, subgraph persistence | `langgraph-persistence` |
| `langgraph new/dev/build/up/deploy`, `langgraph.json` | `langgraph-cli` |
| Replace an LLM routing call with a decision model (TypeSafe, SemIf) | `langgraph-decision-models` |
| Build a Deep Agent: `create_deep_agent()`, harness, config | `deep-agents-core` |
| Deep Agent memory, backends, filesystem | `deep-agents-memory` |
| Deep Agent subagents, todo planning, HITL interrupts | `deep-agents-orchestration` |
| Build/test/deploy Managed Deep Agents on LangSmith | `managed-deep-agents` |
| Run many independent items in parallel (table, fan out, aggregate) | `swarm` |
| Agent evals, benchmarks, Harbor tasks, verifiers, synthetic data | `eval-engineering` |

## Rules

- Combine skills when the task spans rows (e.g. a Deep Agent with persistent memory and subagents = `deep-agents-core` + `deep-agents-memory` + `deep-agents-orchestration`). Load in the order they appear in the task, core first.
- A quickstart skill is only for scaffolding a minimal throwaway agent. For production code, load the fundamentals skill for that framework instead of (or after) the quickstart.
- `langchain-middleware` and `langgraph-human-in-the-loop` both cover approvals but for different frameworks. Match the framework the code actually uses (check imports), not the topic alone.
- If nothing in the table matches (for example plain OpenAI/Anthropic SDK code with no LangChain), load none of these and say so in one line instead of forcing a match.
- If the task is ambiguous between two rows, ask one short question rather than loading both.
