import os,re,sys
root=sys.argv[1]; entry=sys.argv[2]; targets=sys.argv[3:]
src=os.path.join(root,'src')
IMP=re.compile(r'^\s*(import|export)\s+(type\s+)?([^;]*?)\s*from\s*[\'"]([^\'"]+)[\'"]|^\s*import\s*[\'"]([^\'"]+)[\'"]', re.M|re.S)
def resolve(frm, spec):
    if spec.startswith('@/'): base=os.path.join(src,spec[2:])
    elif spec.startswith('@hermes/shared'):
        rest=spec[len('@hermes/shared'):].lstrip('/')
        m={'ansi':'ansi','billing':'billing-types','color':'color','i18n':'i18n','translucency':'translucency'}
        base=os.path.join(root,'..','shared','src',m.get(rest,'index') if rest else 'index')
    elif spec.startswith('.'): base=os.path.join(os.path.dirname(frm),spec)
    else: return None
    for ext in ['','.ts','.tsx','/index.ts','/index.tsx']:
        p=os.path.normpath(base+ext)
        if os.path.isfile(p) and p.endswith(('.ts','.tsx')): return p
    return None
def deps(path):
    s=open(path,encoding='utf-8',errors='ignore').read()
    out=[]
    for m in IMP.finditer(s):
        if m.group(5): out.append(m.group(5)); continue
        if m.group(2): continue
        clause=m.group(3).strip()
        if clause.startswith('{') and clause.endswith('}'):
            names=[n.strip() for n in clause[1:-1].split(',') if n.strip()]
            if names and all(n.startswith('type ') for n in names): continue
        out.append(m.group(4))
    return out
state={}; order=[]
sys.setrecursionlimit(100000)
tset={os.path.normpath(os.path.join(src,t)) for t in targets}
def visit(p, stack):
    if p in state: return
    state[p]='in'; stack.append(p)
    if p in tset:
        print('ENTER', os.path.relpath(p,src), 'stack-has:', [os.path.relpath(x,src) for x in stack if x in tset and x!=p])
    for d in deps(p):
        r=resolve(p,d)
        if r:
            if state.get(r)=='in' and r in tset:
                print('BACKEDGE', os.path.relpath(p,src), '->', os.path.relpath(r,src))
            visit(r, stack)
    stack.pop(); state[p]='done'; order.append(p)
visit(os.path.normpath(os.path.join(src,entry)), [])
for t in targets:
    tp=os.path.normpath(os.path.join(src,t))
    print('EVAL', t, order.index(tp) if tp in order else None)
