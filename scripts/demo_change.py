#!/usr/bin/env python3
import argparse, shutil, json
from rdflib import Graph, URIRef, Literal, RDF, RDFS, OWL
from rdflib.namespace import DCTERMS
from common import ROOT

POL=ROOT/'ontology/ins/policy.ttl'
P='https://data.chubb.com/ontology/ins/policy/'
C='https://data.chubb.com/ontology/fnd/core/'

def reset():
    state=json.loads((ROOT/'governance/release-state.json').read_text())
    rel=ROOT/state['releasePath']
    for folder in ['ontology','vocabulary','shapes']:
        src=rel/folder; dst=ROOT/folder
        if dst.exists(): shutil.rmtree(dst)
        shutil.copytree(src,dst)
    for f in (ROOT/'ontology').rglob('*.ttl'):
        g=Graph(); g.parse(f,format='turtle')
        for ont in list(g.subjects(RDF.type,OWL.Ontology)):
            g.remove((ont,OWL.versionIRI,None)); g.remove((ont,OWL.versionInfo,None)); g.remove((ont,DCTERMS.issued,None))
        g.serialize(f,format='turtle')
    print('Working ontology reset to release',state['currentVersion'])

def add_class():
    g=Graph(); g.parse(POL,format='turtle')
    cyber=URIRef(P+'CyberPolicy')
    if (cyber,RDF.type,OWL.Class) in g: print('CyberPolicy already exists.'); return
    g.add((cyber,RDF.type,OWL.Class)); g.add((cyber,RDFS.subClassOf,URIRef(P+'CommercialPolicy')))
    g.add((cyber,RDFS.label,Literal('Cyber Policy',lang='en')))
    g.add((cyber,RDFS.comment,Literal('Illustrative cyber insurance policy concept added through governed evolution.',lang='en')))
    g.serialize(POL,format='turtle'); print('Added policy:CyberPolicy.')

def breaking():
    g=Graph(); g.parse(POL,format='turtle')
    cp=URIRef(P+'CommercialPolicy'); old=URIRef(P+'Policy'); new=URIRef(C+'Agreement')
    if (cp,RDFS.subClassOf,old) not in g: print('Expected baseline superclass not found; reset first.'); return
    g.remove((cp,RDFS.subClassOf,old)); g.add((cp,RDFS.subClassOf,new)); g.serialize(POL,format='turtle')
    print('Changed CommercialPolicy superclass: Policy -> core:Agreement (breaking example).')

def annotation():
    g=Graph(); g.parse(POL,format='turtle'); policy=URIRef(P+'Policy')
    g.remove((policy,RDFS.comment,None)); g.add((policy,RDFS.comment,Literal('An insurance agreement represented in the enterprise semantic model; demo wording updated.',lang='en')))
    g.serialize(POL,format='turtle'); print('Updated Policy documentation annotation.')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('scenario',choices=['reset','add-class','breaking-superclass','annotation-only']); a=ap.parse_args()
    {'reset':reset,'add-class':add_class,'breaking-superclass':breaking,'annotation-only':annotation}[a.scenario]()
if __name__=='__main__': main()
