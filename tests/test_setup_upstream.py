import importlib.util,subprocess,tempfile,unittest
from pathlib import Path
module_path=Path(__file__).resolve().parents[1]/'tools/setup_upstream.py'
spec=importlib.util.spec_from_file_location('setup_upstream_under_test',module_path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class SourceRecovery(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.source=self.root/'origin'
        self.git('init',str(self.source))
        (self.source/'file.txt').write_text('source\n',encoding='utf-8')
        self.git('-C',str(self.source),'add','file.txt')
        self.git('-C',str(self.source),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','source')
        self.commit=self.git('-C',str(self.source),'rev-parse','HEAD').strip()
        self.url=self.source.as_uri();self.target=self.root/'target'
    def tearDown(self):self.temp.cleanup()
    def git(self,*args):
        return subprocess.check_output(['git',*args],text=True,stderr=subprocess.DEVNULL)
    def test_resume_unborn_checkout_and_then_idempotent(self):
        self.git('init',str(self.target));self.git('-C',str(self.target),'remote','add','origin',self.url)
        module.fetch(self.target,self.url,self.commit)
        self.assertEqual(self.git('-C',str(self.target),'rev-parse','HEAD').strip(),self.commit)
        module.fetch(self.target,self.url,self.commit)
    def test_reject_existing_different_origin(self):
        self.git('init',str(self.target));self.git('-C',str(self.target),'remote','add','origin','https://example.invalid/unrelated')
        with self.assertRaises(RuntimeError):module.fetch(self.target,self.url,self.commit)
    def test_reject_existing_different_commit(self):
        module.fetch(self.target,self.url,self.commit)
        with self.assertRaises(RuntimeError):module.fetch(self.target,self.url,'0'*40)
    def test_preserve_non_git_contents(self):
        self.target.mkdir();file=self.target/'private.txt';file.write_text('preserve',encoding='utf-8')
        with self.assertRaises(RuntimeError):module.fetch(self.target,self.url,self.commit)
        self.assertEqual(file.read_text(),'preserve')
if __name__=='__main__':unittest.main()
