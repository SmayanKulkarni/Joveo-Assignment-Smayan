# 08: `focus` in the Brief

**What to build:** a Run with a `focus` gets a Brief that leads with those Dimensions, while its figures and ratings stay exactly what they'd be without one. Spec: [Brief LLD](../../../docs/lld/brief.md) §9, §15 pass 2.

**Blocked by:** 06: The LLM writer

**Status:** ready-for-agent

- [ ] The writer's input has its `Focus:` line, and the prompt asks it to lead with the focus and give it most Insights
- [ ] `render` moves focused Dimensions first, otherwise keeping the writer's order, and code-added Insights sort with the rest
- [ ] Run Notes list the focus, or "All Dimensions"
- [ ] A test pins that Recommendations, the Outlook, Tags and Stats are unchanged by `focus`
