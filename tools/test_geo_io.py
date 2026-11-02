import gzip
import json
from pathlib import Path
import tempfile
import unittest
from geo_io import read_json,write_json

class LosslessGeometryIOTests(unittest.TestCase):
    def test_compression_preserves_coordinates_and_is_deterministic(self):
        value={'type':'Polygon','coordinates':[[[-121.12345678901234,37.98765432109876],[-121.0,38.0],[-121.12345678901234,37.98765432109876]]]}
        with tempfile.TemporaryDirectory() as tmp:
            a,b=Path(tmp)/'a.geojson.gz',Path(tmp)/'b.geojson.gz'
            write_json(a,value,True);write_json(b,value,True)
            self.assertEqual(a.read_bytes(),b.read_bytes())
            self.assertEqual(read_json(a),value)
            self.assertEqual(json.loads(gzip.decompress(a.read_bytes())),value)

if __name__=='__main__':unittest.main()
