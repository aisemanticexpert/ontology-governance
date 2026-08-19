#!/usr/bin/env python3
from pathlib import Path
import subprocess, time, argparse
from common import ROOT, rdf_files

WATCH_DIRS=['ontology','vocabulary','shapes','samples']
def snapshot():
    return {str(f):f.stat().st_mtime_ns for f in rdf_files(ROOT, WATCH_DIRS)}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--once',action='store_true'); ap.add_argument('--interval',type=float,default=1.0); args=ap.parse_args()
    if args.once: return subprocess.call(['python',str(ROOT/'scripts/govern.py')],cwd=ROOT)
    prev=snapshot(); print('Watching Chubb ontology artifacts. Ctrl+C to stop.'); print('Edit any .ttl or .jsonld under ontology/, vocabulary/, shapes/, or samples/.')
    try:
        while True:
            time.sleep(args.interval); cur=snapshot()
            if cur!=prev:
                changed=sorted(set(cur)^set(prev) | {k for k in cur.keys()&prev.keys() if cur[k]!=prev[k]})
                print('\nChange detected:',', '.join(Path(x).name for x in changed))
                subprocess.call(['python',str(ROOT/'scripts/govern.py')],cwd=ROOT); prev=cur
    except KeyboardInterrupt: print('\nWatcher stopped.')
    return 0
if __name__=='__main__': raise SystemExit(main())
