import json,unittest
from pathlib import Path
from frozen_plan_semantics import assert_same_plan
B=Path(__file__).resolve().parent
class Plans(unittest.TestCase):
 def setUp(self):self.saved=json.loads((B/'fixtures/online-motion-prior-full-v17-frozen.json').read_text(encoding='utf-8'));self.expected=json.loads(json.dumps(self.saved));self.expected['jobs']=[tuple(j) for j in self.expected['jobs']]
 def test_actual_protocol_json_roundtrip(self):assert_same_plan(self.saved,self.expected)
 def test_changed_budget_rejected(self):
  self.saved['jobs'][1][2]=30
  with self.assertRaises(AssertionError):assert_same_plan(self.saved,self.expected)
 def test_changed_code_rejected(self):
  self.saved['scripts']['run_online_v17.py']='0'*64
  with self.assertRaises(AssertionError):assert_same_plan(self.saved,self.expected)
 def test_changed_observation_protocol_rejected(self):
  self.saved['protocol_sha256']='0'*64
  with self.assertRaises(AssertionError):assert_same_plan(self.saved,self.expected)
if __name__=='__main__':unittest.main()
