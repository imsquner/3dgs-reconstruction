"""TokenHub request/response preparation only: no HTTP or credential access."""
import base64
from urllib.parse import urlparse

MODEL='hy-3d-3.1'
SUBMIT_URL='https://tokenhub.tencentmaas.com/v1/api/3d/submit'
QUERY_URL='https://tokenhub.tencentmaas.com/v1/api/3d/query'

def make_request(image_bytes):
    if not image_bytes:raise ValueError('Empty image')
    return {'model':MODEL,'image_base64':base64.b64encode(image_bytes).decode('ascii')}

def normalize_query(response):
    status=response.get('status')
    if status not in ('queued','in_progress','completed','failed'):raise ValueError('Unknown response status')
    if status=='completed':
        glbs=[d for d in response.get('data',[]) if d.get('type','').lower()=='glb']
        if len(glbs)!=1:raise ValueError('Expected one GLB asset')
        parsed=urlparse(glbs[0].get('url',''))
        if parsed.scheme!='https' or not parsed.netloc:raise ValueError('Expected HTTPS GLB download URL')
        return {'state':'succeeded','glb_url':glbs[0]['url']}
    return {'state':{'queued':'queued','in_progress':'running','failed':'failed'}[status],
            'error':response.get('error')}

class SubmissionGuard:
    """Caller must persist begin() state before sending; uncertain is terminal for submit."""
    def __init__(self,saved=None):self.saved=saved or {'state':'prepared','job_id':None}
    def begin(self):
        if self.saved['state']!='prepared':raise RuntimeError('No duplicate submission permitted')
        self.saved={'state':'submission-uncertain','job_id':None}
        return self.saved.copy()
    def record_id(self,job_id):
        if self.saved['state']!='submission-uncertain' or not isinstance(job_id,str) or not job_id:raise ValueError('Unexpected submission result')
        self.saved={'state':'submitted','job_id':job_id};return self.saved.copy()
    def query_body(self):
        if self.saved['state']!='submitted' or not self.saved.get('job_id'):raise RuntimeError('No known job to query')
        return {'model':MODEL,'id':self.saved['job_id']}
