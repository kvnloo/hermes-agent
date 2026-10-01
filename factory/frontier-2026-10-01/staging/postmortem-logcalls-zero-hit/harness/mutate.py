import sys, pathlib
src = pathlib.Path(sys.argv[1]); dst = pathlib.Path(sys.argv[2]); which = sys.argv[3]
s = src.read_text()
M = {
 "N1_require_cache": (r'latency=([\d.]+)s(?: cache=(\d+)/(\d+))?"', r'latency=([\d.]+)s cache=(\d+)/(\d+)"'),
 "N2_no_unavailable": (r'in=(\d+|\?) out=(\d+|\?) total=(?:\d+|\?)', r'in=(\d+) out=(\d+) total=\d+'),
 "N3_no_field_counts": ('return call.get("cache_state") != "no_field"', 'return True'),
 "N4_cache_state_unread": (', ("cache_state", _CACHE_STATE)):', '):'),
 "N5_ratio_over_all": ('sum(c["hit"] for c in scored), sum(c["inp"] for c in scored)', 'sum(c["hit"] for c in calls), sum(c["inp"] for c in calls)'),
 "N6_plateau_unfiltered": ('cs = sorted(filter(_cache_reported, cs), key=lambda c: c["n"])', 'cs.sort(key=lambda c: c["n"])'),
}
old, new = M[which]
assert s.count(old) == 1, which
dst.write_text(s.replace(old, new))
