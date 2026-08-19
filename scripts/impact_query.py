#!/usr/bin/env python3
from rdflib import URIRef, RDF, RDFS, OWL
from common import ROOT, load_graph
import sys

g=load_graph(ROOT,dirs=['ontology','vocabulary','shapes'])
iri=URIRef(sys.argv[1] if len(sys.argv)>1 else 'https://data.chubb.com/ontology/ins/policy/Policy')
print('Impact neighborhood for',iri)
for s,p,o in sorted(g.triples((iri,None,None)),key=lambda x:str(x[1])): print(' OUT',p.n3(),o.n3())
for s,p,o in sorted(g.triples((None,None,iri)),key=lambda x:str(x[1])): print(' IN ',s.n3(),p.n3())
