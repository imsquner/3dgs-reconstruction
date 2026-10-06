import unittest
from quality_mapping_barrier import submit_and_wait,publish_completion

class ChangingCell:
 def __init__(self,values):self.values=list(values)
 def __getitem__(self,index):
  if len(self.values)>1:return self.values.pop(0)
  return self.values[0]

class Barrier(unittest.TestCase):
 def test_waits_until_required_steps(self):
  submitted=[0];done=ChangingCell([0,0,19,20]);calls=[]
  submit_and_wait(submitted,done,0,20,lambda:calls.append(submitted[0]))
  self.assertEqual(submitted,[1]);self.assertEqual(calls,[1,1])
 def test_rejects_missing_previous_observation(self):
  with self.assertRaises(AssertionError):submit_and_wait([0],[0],1,20,lambda:None)
 def test_rejects_unfinished_previous_budget(self):
  with self.assertRaises(AssertionError):submit_and_wait([1],[19],1,20,lambda:None)
 def test_rejects_overshoot(self):
  with self.assertRaises(AssertionError):submit_and_wait([0],ChangingCell([0,21]),0,20,lambda:None)
 def test_publication_requires_cuda_completion(self):
  done=[0];events=[]
  publish_completion([1],done,20,20,lambda:events.append(done[0]))
  self.assertEqual(events,[0]);self.assertEqual(done,[20])
 def test_rejects_unsubmitted_future_work(self):
  with self.assertRaises(AssertionError):publish_completion([1],[20],40,20,lambda:None)
 def test_rejects_skipped_or_partial_budget(self):
  for count in [19,40]:
   with self.assertRaises(AssertionError):publish_completion([2],[0],count,20,lambda:None)
 def test_two_consecutive_frames(self):
  submitted=[0];done=[0]
  for i in range(2):
   def work():publish_completion(submitted,done,(i+1)*20,20,lambda:None)
   submit_and_wait(submitted,done,i,20,work)
  self.assertEqual(done,[40]);self.assertEqual(submitted,[2])

if __name__=='__main__':unittest.main()
