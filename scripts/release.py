#!/usr/bin/env python3
from pathlib import Path
import argparse, json, shutil, re, uuid
from rdflib import Graph, URIRef, Literal, RDF, OWL, Namespace
from common import ROOT, utc_now, ensure_json, git_identity, rdf_files, parse_rdf, rdf_format

PROV=Namespace('http://www.w3.org/ns/prov#'); DCT=Namespace('http://purl.org/dc/terms/'); GOV=Namespace('https://data.chubb.com/ontology/misc/governance/')

def inject_version(ttl_path, version):
    g=parse_rdf(ttl_path)
    onts=list(g.subjects(RDF.type,OWL.Ontology))
    for ont in onts:
        g.remove((ont,OWL.versionIRI,None)); g.remove((ont,OWL.versionInfo,None)); g.remove((ont,DCT.issued,None))
        g.add((ont,OWL.versionIRI,URIRef(str(ont)+version))); g.add((ont,OWL.versionInfo,Literal(version))); g.add((ont,DCT.issued,Literal(utc_now())))
    g.serialize(ttl_path,format=rdf_format(ttl_path))

def main():
    ap=argparse.ArgumentParser(description='Create an immutable approved ontology release')
    ap.add_argument('--approved-by',required=True); ap.add_argument('--ticket',required=True); ap.add_argument('--reason',required=True); ap.add_argument('--change-id'); args=ap.parse_args()
    report=json.loads((ROOT/'reports/latest/change-report.json').read_text())
    if report['status']!='PASS': raise SystemExit('Cannot release: governance report is FAIL.')
    if report['changeLevel']=='NONE': raise SystemExit('Cannot release: no semantic change detected.')
    version=report['suggestedVersion']; out=ROOT/'releases'/version
    if out.exists(): raise SystemExit(f'Release {version} already exists.')
    for folder in ['ontology','vocabulary','shapes']:
        shutil.copytree(ROOT/folder,out/folder)
    for f in rdf_files(out, ['ontology']): inject_version(f,version)
    change_id=args.change_id or f"CHG-{utc_now()[:4]}-{uuid.uuid4().hex[:6].upper()}"
    ident=git_identity(); now=utc_now()
    manifest={'releaseId':f'REL-{version}','version':version,'previousVersion':report['baselineVersion'],'changeId':change_id,'ticket':args.ticket,'reason':args.reason,'approvedBy':args.approved_by,'releasedAt':now,'author':ident,'impact':report['changeLevel'],'changedFiles':report['changedFiles']}
    ensure_json(out/'manifest.json',manifest)
    # PROV change record
    pg=Graph(); change=GOV[change_id]; release=GOV[f'Release-{version}']; agent=URIRef('https://data.chubb.com/resource/agent/'+re.sub(r'[^A-Za-z0-9._-]','-',ident['authorEmail']))
    pg.add((change,RDF.type,PROV.Activity)); pg.add((change,DCT.identifier,Literal(change_id))); pg.add((change,DCT.description,Literal(args.reason))); pg.add((change,PROV.wasAssociatedWith,agent)); pg.add((change,PROV.generated,release)); pg.add((release,RDF.type,PROV.Entity)); pg.add((release,DCT.hasVersion,Literal(version))); pg.add((release,DCT.isVersionOf,URIRef('https://data.chubb.com/ontology/enterprise-bundle'))); pg.add((release,PROV.wasGeneratedBy,change)); pg.add((change,DCT.relation,Literal(args.ticket)))
    provfile=ROOT/'provenance'/f'{change_id}.ttl'; pg.serialize(provfile,format='turtle')
    event={'eventType':'ONTOLOGY_RELEASED','organization':'Chubb','ontologyBundle':'enterprise','previousVersion':report['baselineVersion'],'version':version,'changeId':change_id,'ticket':args.ticket,'impact':report['changeLevel'],'approvedBy':args.approved_by,'releasedAt':now,'changedFiles':report['changedFiles']}
    ensure_json(ROOT/'events'/'ontology-release-latest.json',event)
    state={'currentVersion':version,'releasePath':f'releases/{version}','releasedAt':now,'releaseId':f'REL-{version}','approvedBy':args.approved_by}
    ensure_json(ROOT/'governance/release-state.json',state)
    print(f'Released Chubb ontology bundle {version}')
    print('Immutable release:',out); print('PROV record:',provfile); print('Event:',ROOT/'events/ontology-release-latest.json')
if __name__=='__main__': main()
