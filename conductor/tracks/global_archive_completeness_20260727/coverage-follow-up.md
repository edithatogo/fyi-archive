# Hosted coverage follow-up

PR #253 reported 76.50% patch coverage after the initial push. The uncovered
lines were validation and alternate-input paths in the new source graph and
completeness modules.

Two focused test modules now exercise malformed registries, duplicate and
unresolved mappings, JSONL and wrapper formats, scalar rejection, URL ports,
and synthetic exclusions.

Verification:

- focused result: 20 passed;
- `fyi_archive.source_graph`: 98%;
- `fyi_archive.completeness`: 97%;
- combined focused coverage: 97.83%.
