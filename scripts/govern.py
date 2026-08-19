#!/usr/bin/env python3
from pathlib import Path
import argparse, json, sys
from collections import defaultdict
from rdflib import RDF, RDFS, OWL, URIRef, Literal
from common import ROOT, SH, SKOS, load_graph, load_sample_graph, rdf_files, parse_rdf, semantic_diff, git_identity, bump, utc_now, ensure_json, term

SEMANTIC_PREDICATES_MAJOR = {
    RDFS.subClassOf, RDFS.domain, RDFS.range, OWL.disjointWith, OWL.equivalentClass,
    OWL.inverseOf, OWL.unionOf, OWL.intersectionOf, OWL.complementOf,
    OWL.onProperty, OWL.someValuesFrom, OWL.allValuesFrom, OWL.hasValue,
    OWL.cardinality, OWL.minCardinality, OWL.maxCardinality,
    OWL.qualifiedCardinality, OWL.minQualifiedCardinality, OWL.maxQualifiedCardinality
}
ANNOTATION_PREDICATES = {RDFS.label, RDFS.comment, URIRef('http://purl.org/dc/terms/description'), URIRef('http://www.w3.org/2004/02/skos/core#definition')}
ENTITY_TYPES = {OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty}
SH_CONSTRAINTS = {SH.minCount, SH.maxCount, SH.datatype, SH['class'], SH['in'], SH.pattern, SH.closed, SH.nodeKind, SH.minInclusive, SH.maxInclusive}


def parse_all_ttl(base):
    errors=[]
    for folder in ['ontology','vocabulary','shapes','samples']:
        p=base/folder
        if not p.exists(): continue
        from rdflib import Graph
        for f in rdf_files(base, [folder]):
            try: parse_rdf(f)
            except Exception as e: errors.append(f"{f.relative_to(base)}: {e}")
    return errors

def namespace_checks(g):
    errors=[]; warnings=[]
    chubb='https://data.chubb.com/'
    allowed=('https://data.chubb.com/ontology/','https://data.chubb.com/vocabulary/','https://data.chubb.com/shapes/','https://data.chubb.com/resource/')
    for s,p,o in g:
        for n in (s,p,o):
            if isinstance(n, URIRef) and str(n).startswith(chubb) and not str(n).startswith(allowed):
                errors.append(f"Chubb IRI outside governed roots: {n}")
    # detect obvious version suffix in term local names
    import re
    for s in set(g.subjects(RDF.type, OWL.Class)):
        local=str(s).rstrip('/').split('/')[-1]
        if re.search(r'(_v|Version)[0-9]+$', local, re.I):
            errors.append(f"Version embedded in class IRI: {s}. Keep the class IRI stable; version the ontology release.")
    return sorted(set(errors)), sorted(set(warnings))

def subclass_closure(schema):
    parents=defaultdict(set)
    for c,p in schema.subject_objects(RDFS.subClassOf):
        if isinstance(c, URIRef) and isinstance(p, URIRef): parents[c].add(p)
    changed=True
    while changed:
        changed=False
        for c in list(parents):
            extra=set()
            for p in list(parents[c]): extra |= parents.get(p,set())
            if not extra <= parents[c]: parents[c]|=extra; changed=True
    return parents

def lightweight_shacl(schema, shapes, data):
    # Supports the constraints used by this demo. If pyshacl exists, use it instead.
    try:
        from pyshacl import validate
        merged=schema+data
        conforms, report_graph, report_text = validate(merged, shacl_graph=shapes, inference='rdfs', abort_on_first=False)
        return ([], []) if conforms else ([report_text], [])
    except Exception:
        pass
    errors=[]; warnings=[]
    parents=subclass_closure(schema)
    types=defaultdict(set)
    for n,t in data.subject_objects(RDF.type):
        types[n].add(t); types[n] |= parents.get(t,set())
    for shape in shapes.subjects(RDF.type, SH.NodeShape):
        targets=list(shapes.objects(shape, SH.targetClass))
        pshapes=list(shapes.objects(shape, SH.property))
        for node, nts in types.items():
            if not any(t in nts for t in targets): continue
            for ps in pshapes:
                path=shapes.value(ps, SH.path)
                if not path: continue
                vals=list(data.objects(node,path))
                sev=shapes.value(ps, SH.severity)
                msg=str(shapes.value(ps, SH.message) or f"Constraint failed for {path}")
                bucket=warnings if sev==SH.Warning else errors
                minc=shapes.value(ps,SH.minCount); maxc=shapes.value(ps,SH.maxCount); dt=shapes.value(ps,SH.datatype)
                if minc is not None and len(vals)<int(minc): bucket.append(f"{node}: {msg} (minCount {minc}, found {len(vals)})")
                if maxc is not None and len(vals)>int(maxc): bucket.append(f"{node}: {msg} (maxCount {maxc}, found {len(vals)})")
                if dt is not None:
                    for v in vals:
                        if isinstance(v, Literal):
                            actual = v.datatype
                            # RDF 1.1 plain string literals are equivalent to xsd:string.
                            if str(dt) == 'http://www.w3.org/2001/XMLSchema#string' and actual is None:
                                continue
                            if actual != dt:
                                bucket.append(f"{node}: {msg} (expected datatype {dt}, got {actual})")
    return errors,warnings

def consistency_checks(schema, data):
    errors=[]
    declared=defaultdict(set)
    for s,t in schema.subject_objects(RDF.type):
        if t in ENTITY_TYPES: declared[s].add(t)
    for s,ts in declared.items():
        if len(ts)>1 and OWL.AnnotationProperty not in ts:
            errors.append(f"Entity declared with conflicting OWL entity types: {s} -> {', '.join(map(str,ts))}")
    disjoint=set()
    for a,b in schema.subject_objects(OWL.disjointWith): disjoint.add((a,b)); disjoint.add((b,a))
    parents=subclass_closure(schema)
    # class cannot inherit from two disjoint ancestors
    for c,anc in parents.items():
        vals=set(anc)|{c}
        for a,b in disjoint:
            if a in vals and b in vals: errors.append(f"Class {c} is under disjoint classes {a} and {b}")
    # data instance typed disjointly (including inherited types)
    for n in set(data.subjects(RDF.type,None)):
        ts=set(data.objects(n,RDF.type)); expanded=set(ts)
        for t in ts: expanded |= parents.get(t,set())
        for a,b in disjoint:
            if a in expanded and b in expanded: errors.append(f"Instance {n} is typed under disjoint classes {a} and {b}")
    return sorted(set(errors))

def classify(old_only,new_only):
    reasons=[]; level='NONE'
    rank={'NONE':0,'PATCH':1,'MINOR':2,'MAJOR':3}
    added_entities={s for s,p,o in new_only if p==RDF.type and o in ENTITY_TYPES}
    def promote(l,r):
        nonlocal level
        if rank[l]>rank[level]: level=l
        reasons.append((l,r))
    for s,p,o in old_only:
        if p==RDF.type and o in ENTITY_TYPES: promote('MAJOR',f"Removed ontology entity {s} ({o})")
        elif p==RDF.type and o==SKOS.Concept: promote('MAJOR',f"Removed governed SKOS concept {s}")
        elif p in SEMANTIC_PREDICATES_MAJOR: promote('MAJOR',f"Removed semantic axiom: {term(s)} {term(p)} {term(o)}")
        elif p in SH_CONSTRAINTS: promote('MAJOR',f"Removed/changed SHACL constraint: {term(p)} {term(o)}")
        elif p in ANNOTATION_PREDICATES: promote('PATCH',f"Removed/changed annotation on {s}")
        else: promote('MINOR',f"Removed RDF statement affecting {s}")
    for s,p,o in new_only:
        if p==RDF.type and o in ENTITY_TYPES: promote('MINOR',f"Added ontology entity {s} ({o})")
        elif p==RDF.type and o==SKOS.Concept: promote('MINOR',f"Added SKOS concept {s}")
        elif p in SEMANTIC_PREDICATES_MAJOR:
            if s in added_entities:
                promote('MINOR',f"Defined new entity with semantic axiom: {term(s)} {term(p)} {term(o)}")
            else:
                promote('MAJOR',f"Added/changed inference-sensitive axiom on existing entity: {term(s)} {term(p)} {term(o)}")
        elif p in SH_CONSTRAINTS:
            if p in {SH.minCount,SH.maxCount,SH.closed,SH['in']}:
                promote('MAJOR',f"Added/tightened data acceptance constraint: {term(p)} {term(o)}")
            else: promote('MINOR',f"Added SHACL constraint: {term(p)} {term(o)}")
        elif p in ANNOTATION_PREDICATES: promote('PATCH',f"Added/changed annotation on {s}")
        else: promote('MINOR',f"Added RDF statement affecting {s}")
    return level,reasons

def changed_files(base_old, base_new=ROOT):
    # Compare RDF meaning, not bytes. Release metadata and Turtle formatting are ignored.
    from rdflib import Graph
    out=[]
    for folder in ['ontology','vocabulary','shapes']:
        files=set()
        op=base_old/folder; np=base_new/folder
        files |= {f.relative_to(base_old) for f in rdf_files(base_old, [folder])}
        files |= {f.relative_to(base_new) for f in rdf_files(base_new, [folder])}
        for rel in sorted(files):
            a=base_old/rel; b=base_new/rel
            if not a.exists() or not b.exists():
                out.append(str(rel)); continue
            ga=parse_rdf(a); gb=parse_rdf(b)
            old_only,new_only=semantic_diff(ga,gb)
            if old_only or new_only: out.append(str(rel))
    return out

def main():
    ap=argparse.ArgumentParser(description='Chubb ontology governance quality gate')
    ap.add_argument('--ci', action='store_true')
    args=ap.parse_args()
    state=json.loads((ROOT/'governance/release-state.json').read_text())
    baseline=ROOT/state['releasePath']
    parse_errors=parse_all_ttl(ROOT)
    report={'timestamp':utc_now(),'baselineVersion':state['currentVersion'],'baselinePath':state['releasePath'],'identity':git_identity()}
    if parse_errors:
        report.update(status='FAIL',errors=parse_errors); ensure_json(ROOT/'reports/latest/change-report.json',report)
        print('ONTOLOGY GOVERNANCE: FAIL - syntax errors'); [print('ERROR:',e) for e in parse_errors]; return 2
    old=load_graph(baseline); new=load_graph(ROOT)
    old_only,new_only=semantic_diff(old,new)
    level,reasons=classify(old_only,new_only)
    ns_errors,ns_warnings=namespace_checks(new)
    data=load_sample_graph(ROOT)
    shapes_only=load_graph(ROOT,dirs=['shapes']); schema_only=load_graph(ROOT,dirs=['ontology','vocabulary'])
    sh_errors,sh_warnings=lightweight_shacl(schema_only,shapes_only,data)
    consistency=consistency_checks(schema_only,data)
    errors=ns_errors+sh_errors+consistency
    warnings=ns_warnings+sh_warnings
    changed=changed_files(baseline)
    suggested=bump(state['currentVersion'],level)
    report.update(
      status='PASS' if not errors else 'FAIL', changeLevel=level, suggestedVersion=suggested,
      changedFiles=changed, removedTriples=len(old_only), addedTriples=len(new_only),
      reasons=[{'level':l,'reason':r} for l,r in reasons[:100]], errors=errors,warnings=warnings,
      governanceDecision=('NO_RELEASE' if level=='NONE' else ('AUTO_REVIEW' if level=='PATCH' else 'REQUIRES_APPROVAL'))
    )
    ensure_json(ROOT/'reports/latest/change-report.json',report)
    lines=[
      '# Chubb Ontology Change Report','',f"Generated: {report['timestamp']}",f"Baseline: {state['currentVersion']}",
      f"Status: **{report['status']}**",f"Detected impact: **{level}**",f"Suggested release: **{suggested}**",'',
      '## Changed files',*( [f'- `{x}`' for x in changed] or ['- None'] ),'',
      '## Semantic changes',*( [f'- **{l}** - {r}' for l,r in reasons[:50]] or ['- No semantic change'] ),'',
      '## Validation errors',*( [f'- {x}' for x in errors] or ['- None'] ),'',
      '## Warnings',*( [f'- {x}' for x in warnings] or ['- None'] ),'',
      '## Governance action',f"`{report['governanceDecision']}`"
    ]
    (ROOT/'reports/latest/change-report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('='*72); print('CHUBB ENTERPRISE ONTOLOGY GOVERNANCE GATE'); print('='*72)
    print('Baseline version :',state['currentVersion']); print('Changed files    :',len(changed)); print('Semantic impact  :',level); print('Suggested version:',suggested); print('Validation       :',report['status'])
    if changed:
        for x in changed: print('  changed:',x)
    for l,r in reasons[:12]: print(f'  {l}: {r}')
    for w in warnings: print('  WARNING:',w)
    for e in errors: print('  ERROR:',e)
    print('Report:',ROOT/'reports/latest/change-report.md')
    return 0 if not errors else 2

if __name__=='__main__': sys.exit(main())
