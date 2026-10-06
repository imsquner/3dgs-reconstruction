import unittest,multiprocessing as mp

def child_draw(seed,queue):
 from worker_seed import seed_worker
 import random,numpy as np,torch
 seed_worker(seed)
 queue.put((random.random(),float(np.random.rand()),float(torch.rand(1))))

class WorkerSeedTests(unittest.TestCase):
 def draw(self,seed):
  ctx=mp.get_context('spawn');queue=ctx.Queue();child=ctx.Process(target=child_draw,args=(seed,queue))
  child.start();result=queue.get(timeout=30);child.join(timeout=30)
  self.assertEqual(child.exitcode,0);queue.close();return result
 def test_spawned_workers_receive_explicit_seed(self):
  first=self.draw(37);self.assertEqual(first,self.draw(37));self.assertNotEqual(first,self.draw(38))

if __name__=='__main__':unittest.main()
