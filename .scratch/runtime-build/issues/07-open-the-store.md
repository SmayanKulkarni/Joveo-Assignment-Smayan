# 07: Open the Store and reach it from a node

**What to build:** the Run Controller opens the Store on the runs database, and a node behind `owned()` can read and write it through `runtime.store`, so a value written during one Run is there for the next. The core Run path doesn't change. What the Store holds and which nodes read it belong to the Long-term memory LLD. See [Opening the Store](../../runtime-lld/issues/06-opening-the-store.md) and `docs/lld/runtime.md` §4, §11 and §16.

**Blocked by:** None (can start immediately). It changes the Run Controller and the graph wiring, so run it after any session editing those.

**Status:** done

- [x] A value written through `runtime.store` on one thread is read on another after the Controller reopens
- [x] A Pause still resumes correctly with the Store open
- [x] The Store's connection is autocommit, and a test fails if it isn't
- [x] The Store's `setup()` uses the saver's retry
- [x] Values are stored as plain JSON, and nothing joins the msgpack allowlist
