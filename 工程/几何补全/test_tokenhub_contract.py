import unittest
from tokenhub_contract import make_request, normalize_query, SubmissionGuard

class TokenHubTests(unittest.TestCase):
    def test_raw_base64_not_data_url(self):
        r=make_request(b'jpeg-fixture')
        self.assertEqual(r['model'],'hy-3d-3.1')
        self.assertFalse(r['image_base64'].startswith('data:'))
        self.assertEqual(set(r),{'model','image_base64'})
    def test_completed_without_glb_is_not_success(self):
        with self.assertRaises(ValueError):normalize_query({'status':'completed','data':[{'type':'obj','url':'https://example.com/o.obj'}]})
    def test_failed_stops(self):
        self.assertEqual(normalize_query({'status':'failed','error':{'message':'bad mesh'}})['state'],'failed')
    def test_reject_unexpected_status(self):
        with self.assertRaises(ValueError):normalize_query({'status':'mystery'})
    def test_submission_uncertain_never_retried(self):
        g=SubmissionGuard();g.begin()
        with self.assertRaises(RuntimeError):g.begin()
    def test_resume_known_job_queries_only(self):
        g=SubmissionGuard({'state':'submitted','job_id':'mock-job'})
        with self.assertRaises(RuntimeError):g.begin()
        self.assertEqual(g.query_body(),{'model':'hy-3d-3.1','id':'mock-job'})

if __name__=='__main__':unittest.main()
