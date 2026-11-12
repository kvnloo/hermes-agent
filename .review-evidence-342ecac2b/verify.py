import hashlib,json,pathlib,sqlite3,sys
root=pathlib.Path(__file__).parent
v3=root/'evidence/firstmate-causality/v3'
m=json.loads((v3/'run-manifest.json').read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
errs=[]; observed=[]
for r in m['runs']:
 p=root/r['rawPath']; d=json.loads(p.read_text())
 if sha(p)!=r['rawSha256']: errs.append(('raw_hash',r['runId']))
 calls=[]; results=[]
 for sess in d.get('sessions',[]):
  for msg in sess.get('messages',[]):
   text=' '.join(str(msg.get(k,'')) for k in ('content','tool_calls','name'))
   if 'kanban_create' in text: calls.append(text[:500])
   if 't_' in text: results.append(text[:500])
 observed.append((r['runId'],r['created'],r['createdTaskIds'],len(calls),len(results),len(d.get('sessions',[]))))
if sha(v3/'isolated-board.db')!=m['isolatedBoard']['sha256']: errs.append(('board_hash',sha(v3/'isolated-board.db')))
con=sqlite3.connect(f"file:{v3/'isolated-board.db'}?mode=ro",uri=True)
tasks=con.execute('select id,title,status,created_by from tasks order by created_at').fetchall()
events=con.execute('select task_id,kind,payload from task_events order by id').fetchall(); con.close()
prod=pathlib.Path(m['productionSentinel']['path'])
con=sqlite3.connect(f'file:{prod}?mode=ro',uri=True); con.execute('pragma query_only=on')
ids=m['productionSentinel']['isolatedTaskIdsSearched']; q=','.join('?'*len(ids))
collisions=con.execute(f'select id from tasks where id in ({q})',ids).fetchall()
markers=con.execute("select count(*) from tasks where title like '%focused-allowlist replay documentation%' or body like '%FIRSTMATE MATCHED INTAKE REPLAY%'").fetchone()[0]; con.close()
print(json.dumps({'errors':errs,'observed':observed,'tasks':tasks,'events':events,'production_current_sha':sha(prod),'production_collisions':collisions,'production_markers':markers},indent=2,default=str))
sys.exit(bool(errs or collisions or markers))
