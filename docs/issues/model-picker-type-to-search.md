# Model picker should filter immediately as the user types

## Summary

`hermes model` can expose long provider and model catalogs, but the curses picker currently requires `/` before a query can be entered. That extra mode switch is easy to miss and makes selecting a known provider/model slower than necessary.

## Expected behavior

In the provider and model pickers:

- typing a printable character immediately starts filtering;
- matching remains case-insensitive and fuzzy, using the existing ranked search;
- Up/Down continue to move through the filtered rows;
- Enter or Space selects the highlighted concrete row;
- Escape cancels the picker, including while a filter is active;
- the returned value remains the original catalog index, never a filtered-list position or an inferred ambiguous model;
- `/` remains accepted as an explicit search shortcut for compatibility.

The numbered non-curses fallback should remain unchanged.

## Current behavior

The model list advertises `/ search`. Printable keys outside explicit search mode are interpreted as navigation shortcuts or ignored. The provider list is not searchable.

## Proposed implementation

1. In the shared searchable radiolist loop, activate search and seed the query when a printable non-space character is typed.
2. Reserve Space for selection both before and after filtering.
3. Route Escape through the existing menu cancellation path rather than treating it as “clear search.”
4. Enable the shared searchable radiolist for the `hermes model` provider picker.
5. Add integration-style key-sequence tests covering immediate filtering, filtered Up/Down navigation, Enter/Space selection, original-index preservation, and Escape cancellation.

## Acceptance criteria

- A user can type part of a provider or model name without first pressing `/`.
- Filtering updates after the first typed character.
- Keyboard navigation and selection operate on the visible filtered results.
- Selection resolves exactly to the highlighted provider/model entry.
- Escape returns the picker’s cancellation value.
- Existing non-searchable menus and numbered fallbacks do not change.
