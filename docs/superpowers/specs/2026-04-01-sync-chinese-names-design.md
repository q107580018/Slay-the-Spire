Title: Sync Chinese Card Names Design

Summary

Goal: For the ironclad-full-cards plan, fetch authoritative Chinese card names from the referenced wikis and update content/cards/ironclad_starter.json and content/cards/curses.json (only the name fields) to match the source. Record any cards not found.

Scope

- Target card ids are taken from docs/superpowers/plans/2026-03-31-ironclad-full-cards.md (common, uncommon, rare lists and wound/dazed). Only cards present in content/cards/ironclad_starter.json and content/cards/curses.json are candidates for update.
- Only update the `name` fields. Do not modify other fields or card ids.
- For upgraded variants (ids ending with `_plus` or other upgrade suffixes), map the base Chinese name to base id and append a postfix like `+` for the upgraded version if that matches the wiki.

Approach Options

1) Scripted browser automation (recommended)
   - Use the agent-browser skill to search the HuijiWiki (sts.huijiwiki.com) first, then fallback to Fandom if not found.
   - Parse the page title and/or infobox Chinese name. For cards with '+' variants, detect whether the wiki has a `+` form and use that directly; otherwise append `+` to base Chinese name for upgraded id.
   - Advantages: robust for sites requiring JS, deterministic navigation. Slightly more work to script.

2) Simple HTTP fetch (faster, fragile)
   - Use webfetch to request known wiki URLs and parse returned HTML for the Chinese name.
   - Advantages: faster and simpler. Disadvantages: may fail on JS-heavy pages or redirects.

Recommendation: Use agent-browser automation to ensure accurate extraction (HuijiWiki is static but fandom sometimes redirects / JS). Implement a small lookup order: HuijiWiki -> Fandom -> skip.

Data Mapping Rules

- For id `foo` and `foo_plus`:
  - If wiki lists a Chinese name for the upgraded version explicitly (e.g., `身体重击+`), use that.
  - Else, take base Chinese name and append `+`.
- Preserve existing name if no authoritative name is found.

Process

1. Extract the target id list from the plan markdown (manual selection of common/uncommon/rare and wound/dazed). Use the set to limit lookups.
2. For each id, search HuijiWiki using the card's English id or name as query. Extract Chinese canonical name.
3. For each card entry in the two JSON files, compare and update the `name` field when different.
4. Run pytest. If tests fail, revert content changes and report failure (but we will update only name fields which should not affect logic most likely; still run tests).
5. Commit changes with message: "chore(content): sync card Chinese names with reference wiki"

Outputs / Report

- List of updated cards with (id, old name, new name)
- List of card ids not found
- Pytest results
- Commit hash

Safety and Constraints

- Only modify the two JSON files. Keep all other files unchanged.
- If extraction ambiguous, prefer leaving the existing name and record as not found.
- Use agent-browser for web retrieval where necessary.

Next Step

- With your approval I will implement the scripted automation: extract target ids, fetch names, update the two JSON files, run pytest, and commit. I will use agent-browser for robust scraping and fall back to webfetch if possible.

Please confirm to proceed.
