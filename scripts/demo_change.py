#!/usr/bin/env python3
import argparse, shutil, json
from rdflib import Graph, URIRef, Literal, RDF, RDFS, OWL
from rdflib.namespace import DCTERMS
from common import ROOT, rdf_files, parse_rdf, rdf_format

P='https://data.chubb.com/ontology/ins/policy/'
C='https://data.chubb.com/ontology/fnd/core/'

def policy_path():
    for suffix in ('.ttl', '.jsonld'):
        path=ROOT/'ontology/ins'/f'policy{suffix}'
        if path.exists(): return path
    raise FileNotFoundError('Expected ontology/ins/policy.ttl or policy.jsonld')

def reset():
    state=json.loads((ROOT/'governance/release-state.json').read_text())
    rel=ROOT/state['releasePath']
    for folder in ['ontology','vocabulary','shapes']:
        src=rel/folder; dst=ROOT/folder
        if dst.exists(): shutil.rmtree(dst)
        shutil.copytree(src,dst)
    for f in rdf_files(ROOT, ['ontology']):
        g=parse_rdf(f)
        for ont in list(g.subjects(RDF.type,OWL.Ontology)):
            g.remove((ont,OWL.versionIRI,None)); g.remove((ont,OWL.versionInfo,None)); g.remove((ont,DCTERMS.issued,None))
        g.serialize(f,format=rdf_format(f))
    print('Working ontology reset to release',state['currentVersion'])

def add_class():
    path=policy_path(); g=parse_rdf(path)
    cyber=URIRef(P+'CyberPolicy')
    if (cyber,RDF.type,OWL.Class) in g: print('CyberPolicy already exists.'); return
    g.add((cyber,RDF.type,OWL.Class)); g.add((cyber,RDFS.subClassOf,URIRef(P+'CommercialPolicy')))
    g.add((cyber,RDFS.label,Literal('Cyber Policy',lang='en')))
    g.add((cyber,RDFS.comment,Literal('Illustrative cyber insurance policy concept added through governed evolution.',lang='en')))
    g.serialize(path,format=rdf_format(path)); print('Added policy:CyberPolicy.')

def breaking():
    path=policy_path(); g=parse_rdf(path)
    cp=URIRef(P+'CommercialPolicy'); old=URIRef(P+'Policy'); new=URIRef(C+'Agreement')
    if (cp,RDFS.subClassOf,old) not in g: print('Expected baseline superclass not found; reset first.'); return
    g.remove((cp,RDFS.subClassOf,old)); g.add((cp,RDFS.subClassOf,new)); g.serialize(path,format=rdf_format(path))
    print('Changed CommercialPolicy superclass: Policy -> core:Agreement (breaking example).')

def annotation():
    path=policy_path(); g=parse_rdf(path); policy=URIRef(P+'Policy')
    g.remove((policy,RDFS.comment,None)); g.add((policy,RDFS.comment,Literal('An insurance agreement represented in the enterprise semantic model; demo wording updated.',lang='en')))
    g.serialize(path,format=rdf_format(path)); print('Updated Policy documentation annotation.')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('scenario',choices=['reset','add-class','breaking-superclass','annotation-only']); a=ap.parse_args()
    {'reset':reset,'add-class':add_class,'breaking-superclass':breaking,'annotation-only':annotation}[a.scenario]()
if __name__=='__main__': main()
