"""Run the existing installed-plugin replay algorithm on the frozen private inputs."""
import importlib.util
import json
from pathlib import Path

here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('replayed_skill_rank', here / 'profile/plugins/skill-rank/__init__.py')
rank = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rank)
labels = [json.loads(line) for line in (here / 'labels-noedit.jsonl').read_text().splitlines()]
hits = fired = 0
for row in labels:
    output = rank.suggest(row['q'])
    fired += bool(output)
    hits += any(f'skill_view(name="{name}")' in output for name in row['skills'])
print(json.dumps({'docs': len(rank.load_docs()), 'n': len(labels), 'fired': fired,
                  'hits_at_3': hits, 'hit_at_3': hits / len(labels),
                  'labels': 'historical agent choices, not expert ground truth'}))
