# 13: Keep the places the user chose

**What to build:** a Brief headed "Mumbai" can no longer rest on a country-wide search. Broaden keeps the user's place, and only the user can go wider. Spec: [Collection LLD](../../../docs/lld/collection.md) §9, §10. Built on today's single `location`, so it ships even if the many-places ticket doesn't.

**Blocked by:** none

**Status:** done

- [x] `broaden` pins `location` in code beside `country` and `target_postings`
- [x] `BROADEN_SYSTEM` loses the country-wide move and says each title is one job title
- [x] `LowDataAnswer.whole_country` defaults to false, and a checkbox on the low-data card sets it, shown only when the plan has a place
- [x] Tests: broaden can't blank the place, the checkbox can, and an old checkpoint still loads
