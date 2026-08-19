from pathlib import Path
import json, os, subprocess, hashlib, datetime
from rdflib import Graph, URIRef, RDF, RDFS, OWL, Namespace, Literal
from rdflib.compare import graph_diff, to_isomorphic

ROOT = Path(__file__).resolve().parents[1]
SH = Namespace("http://www.w3.org/ns/shacl#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
PROV = Namespace("http://www.w3.org/ns/prov#")
DCT = Namespace("http://purl.org/dc/terms/")
EXG = Namespace("https://data.chubb.com/ontology/misc/governance/")

ARTIFACT_DIRS = ["ontology", "vocabulary", "shapes"]
IGNORE_PREDICATES = {OWL.versionIRI, OWL.versionInfo, DCT.issued, DCT.modified}


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()

def load_graph(base: Path, dirs=ARTIFACT_DIRS):
    g=Graph()
    for d in dirs:
        p=base/d
        if not p.exists(): continue
        for f in sorted(p.rglob('*.ttl')):
            g.parse(f, format='turtle')
    return g

def load_sample_graph(base: Path):
    g=Graph()
    p=base/'samples'
    if p.exists():
        for f in sorted(p.rglob('*.ttl')): g.parse(f, format='turtle')
    return g

def semantic_diff(old: Graph, new: Graph):
    # Ignore generated release metadata before canonical graph diff.
    def filtered(g):
        x=Graph()
        for t in g:
            if t[1] not in IGNORE_PREDICATES: x.add(t)
        return x
    both, old_only, new_only = graph_diff(to_isomorphic(filtered(old)), to_isomorphic(filtered(new)))
    return set(old_only), set(new_only)

def term(s):
    return s.n3() if hasattr(s,'n3') else str(s)

def git_identity():
    def cmd(args):
        try: return subprocess.check_output(args, cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
        except Exception: return ''
    return {
      'authorName': cmd(['git','config','user.name']) or os.getenv('GIT_AUTHOR_NAME') or os.getenv('USER') or 'unknown-user',
      'authorEmail': cmd(['git','config','user.email']) or os.getenv('GIT_AUTHOR_EMAIL') or 'unknown@example.invalid',
      'commit': cmd(['git','rev-parse','--short','HEAD']) or 'working-tree'
    }

def bump(version, level):
    major,minor,patch=[int(x) for x in version.split('.')]
    if level=='MAJOR': return f"{major+1}.0.0"
    if level=='MINOR': return f"{major}.{minor+1}.0"
    if level=='PATCH': return f"{major}.{minor}.{patch+1}"
    return version

def sha256_file(p: Path):
    h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()

def ensure_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(obj, indent=2)+"\n", encoding='utf-8')
