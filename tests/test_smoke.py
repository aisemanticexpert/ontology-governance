import json
import subprocess
import sys
from pathlib import Path
from rdflib import Graph, URIRef, RDF, OWL

from scripts.common import load_graph

ROOT = Path(__file__).resolve().parents[1]


def test_governance_baseline_passes():
    result = subprocess.run(
        [sys.executable, "scripts/govern.py", "--ci"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    report = json.loads((ROOT / "reports/latest/change-report.json").read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["changeLevel"] == "NONE"
    assert report["suggestedVersion"] == report["baselineVersion"]


def test_jsonld_artifacts_are_loaded(tmp_path):
    ontology = tmp_path / "ontology"
    ontology.mkdir()
    graph = Graph()
    entity = URIRef("https://data.chubb.com/ontology/test/JsonLdEntity")
    graph.add((entity, RDF.type, OWL.Class))
    graph.serialize(ontology / "entity.jsonld", format="json-ld")

    loaded = load_graph(tmp_path)

    assert (entity, RDF.type, OWL.Class) in loaded
