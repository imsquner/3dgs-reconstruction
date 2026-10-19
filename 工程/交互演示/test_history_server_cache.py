import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
import server
class CacheTest(unittest.TestCase):
 def test_repeat_and_invalidation(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);p=root/'snapshot-index.json';p.write_text(json.dumps({'snapshots':[{'ply':'snapshots/a.ply'}]}))
   original=server.json.loads
   with patch.object(server.json,'loads',wraps=original) as read:
    self.assertEqual(server.history_allowed(root),frozenset(['snapshots/a.ply']));server.history_allowed(root);self.assertEqual(read.call_count,1)
    p.write_text(json.dumps({'snapshots':[{'ply':'snapshots/changed.ply'}]}));self.assertEqual(server.history_allowed(root),frozenset(['snapshots/changed.ply']));self.assertEqual(read.call_count,2)
if __name__=='__main__':unittest.main()
