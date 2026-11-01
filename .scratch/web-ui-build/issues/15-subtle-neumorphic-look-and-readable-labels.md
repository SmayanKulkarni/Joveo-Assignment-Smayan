# 15: Subtle neumorphic look and readable labels

**What to build:** the whole app takes the new tokens, the plan editor fits one screen, and no raw value shows. Spec: [Web UI LLD](../../../docs/lld/web-ui.md) §15. The [look prototype](../../web-ui/prototype/look/index.html) holds the CSS to carry over. Ships with a single place input until ticket 17 turns it into chips.

**Blocked by:** none

**Status:** done

- [x] Tokens in `styles.css`, with real borders, a solid focus ring and a clear disabled state
- [x] `labels.ts` with the category table, and country names from `Intl.DisplayNames`, in the editor, plan card and Run Notes
- [x] Editor: title chips with an add box, 4-column grid, radius and days selects that keep a non-preset value
- [x] Print: no shadows, white background
- [x] Checked by hand on a Demo Run at desktop and phone width, with keyboard focus visible everywhere
