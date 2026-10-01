import tools.fuzzy_match as fm
print("context_aware in SIMILARITY_STRATEGIES:", "context_aware" in fm.SIMILARITY_STRATEGIES, "floor:", fm._FUZZY_CONTENT_FLOOR)
calls = []
orig = fm._normalized_similarity
def spy(region, pattern):
    r = orig(region, pattern); calls.append((region, pattern, round(r, 3))); return r
fm._normalized_similarity = spy
cases = {
  "single_line_wrong_token": ("def f(v):\n    return value.strip()\n", "    return value.trim()", "    return value.fixed()"),
  "single_line_missing_anchor": ("def normalize(value):\n    return value.strip()\n", "return value.trim()", "return value.casefold()"),
  "single_line_trailing_newline": ("def f(v):\n    return value.strip()\n", "    return value.trim()\n", "    return value.fixed()\n"),
  "block_anchor_middle": ("def handler(request):\n    audit_log(request.user_id)\n    return process(request)\n", "def handler(request):\n    validate(request.token)\n    return process(request)", "def handler(request):\n    rate_limit(request)\n    return process(request)"),
}
for name, (c, o, n) in cases.items():
    calls.clear()
    new, count, strat, err = fm.fuzzy_find_and_replace(c, o, n)
    print(f"{name}: strategy={strat} count={count} err={err!r} floor_calls={calls}")
