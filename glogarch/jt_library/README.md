Content packs in this directory ship with jt-glogarch and appear in everyone's Jason Tools
tab. Only packs the owner agreed to publish belong here; `tests/test_packs.py` lists their ids
and fails on any other. A site's own packs live in the local library next to the database
(`jt-library/`), which is never published.

`guide-notes.i18n` holds the translated guide text for these packs only. It is not named
`*.json`, so the library does not take it for a pack.
