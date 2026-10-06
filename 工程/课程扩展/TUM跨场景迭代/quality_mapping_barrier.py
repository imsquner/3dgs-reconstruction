"""Observation completion boundary, independent of host scheduling and future frames."""
def submit_and_wait(submitted,completed,index,budget,pause):
 assert budget>0 and index>=0
 assert int(submitted[0])==index,'Observation submission must be ordered'
 assert int(completed[0])==index*budget,'Previous observation budget incomplete'
 submitted[0]=index+1
 expected=(index+1)*budget
 while int(completed[0])<expected:pause()
 assert int(completed[0])==expected,'Mapping overshot submitted observation'

def publish_completion(submitted,completed,steps,budget,synchronize):
 assert budget>0 and steps==int(completed[0])+budget
 assert steps<=int(submitted[0])*budget,'Future observation not submitted'
 synchronize()
 completed[0]=steps

def install_barrier_references(tracker_class,mapper_class):
 for cls in [tracker_class,mapper_class]:
  previous=cls.__init__
  def wrapped(self,system,_previous=previous):
   _previous(self,system)
   self.quality_observation_submitted=system.quality_observation_submitted
   self.quality_mapping_completed=system.quality_mapping_completed
  cls.__init__=wrapped
