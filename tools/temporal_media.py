#!/usr/bin/env python3
"""Build the separate media race-call master from exact cached observations."""
import argparse
import json
from pathlib import Path
from temporal.media_evidence import MediaEvidenceStore
from temporal.media_results import collect,write


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--online',action='store_true',help='Acquire fresh actual media responses; default is offline replay')
 parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'temporal-data'/'media-results')
 parser.add_argument('--export-evidence',type=Path)
 parser.add_argument('--uncompressed-json',action='store_true',help='Write plain JSON instead of the default lossless gzip publication')
 args=parser.parse_args();store=MediaEvidenceStore();result=collect(store,offline=not args.online)
 manifest=write(result,args.output,compressed=not args.uncompressed_json)
 if args.export_evidence:store.export(result['sourceObservations'],args.export_evidence)
 print(json.dumps(dict(output=str(args.output),datasetId=result['datasetId'],coverage=manifest['coverage']),indent=2))


if __name__=='__main__':main()
