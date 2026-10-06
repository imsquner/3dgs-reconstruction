import hashlib,io,json,sys,tarfile,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import download_assets as d

class Assets(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.cache=self.root/'cache'
    def tearDown(self): self.tmp.cleanup()
    def item(self,data,name='bundle.zip'):
        return dict(id='website-core',name=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),url='https://example.test/'+name,format='zip',target='.')
    def zip(self,members):
        path=self.root/'bundle.zip'
        with zipfile.ZipFile(path,'w') as z:
            for name,data in members: z.writestr(name,data)
        return path
    def test_offline_and_corrupt_cache(self):
        self.cache.mkdir(); data=b'abc'; item=self.item(data); (self.cache/item['name']).write_bytes(data)
        self.assertEqual(d.download(item,self.cache,True),self.cache/item['name'])
        (self.cache/item['name']).write_bytes(b'bad')
        with self.assertRaises(ValueError): d.download(item,self.cache,True)
    def test_resume(self):
        data=b'abcdef'; item=self.item(data); self.cache.mkdir()
        (self.cache/'bundle.zip.partial').write_bytes(data[:3]); (self.cache/'bundle.zip.checkpoint.json').write_text(json.dumps({k:item[k] for k in ('name','bytes','sha256','url')}))
        class Response(io.BytesIO):
            status=206; headers={'Content-Range':'bytes 3-5/6'}
        def response(req,**kw):
            self.assertEqual(req.headers['Range'],'bytes=3-'); return Response(data[3:])
        with patch.object(d.urllib.request,'urlopen',response): self.assertEqual(d.download(item,self.cache).read_bytes(),data)
        self.assertFalse((self.cache/'bundle.zip.partial').exists())
    def test_checksum_failure_no_final(self):
        class Response(io.BytesIO): status=200; headers={}
        with patch.object(d.urllib.request,'urlopen',return_value=Response(b'bad')):
            with self.assertRaises(ValueError): d.download(self.item(b'abc'),self.cache)
        self.assertFalse((self.cache/'bundle.zip').exists())
    def test_paths_and_partial_install(self):
        with self.assertRaises(ValueError): d.safe_path(self.root,'a\\evil')
        for name in ('../evil','/evil','C:/evil'):
            path=self.zip([('good',b'ok'),(name,b'bad')]); target=self.root/'target'
            with self.assertRaises(ValueError): d.install(path,self.item(path.read_bytes()),target,[])
            self.assertFalse((target/'good').exists())
    def test_tar_links(self):
        path=self.root/'x.tar.gz'
        with tarfile.open(path,'w:gz') as t:
            m=tarfile.TarInfo('link'); m.type=tarfile.SYMTYPE; m.linkname='/tmp'; t.addfile(m)
        item=self.item(path.read_bytes()); item['format']='tar.gz'
        with self.assertRaises(ValueError): d.install(path,item,self.root/'target',[])
    def test_windows_names(self):
        for name in ('NUL','a/COM1.txt','a../x','a /x'):
            with self.assertRaises(ValueError): d.safe_path(self.root,name)
    def test_server_ignores_range(self):
        data=b'abcdef'; item=self.item(data); self.cache.mkdir()
        (self.cache/'bundle.zip.partial').write_bytes(b'abc')
        (self.cache/'bundle.zip.checkpoint.json').write_text(json.dumps({k:item[k] for k in ('name','bytes','sha256','url')}))
        class Response(io.BytesIO): status=200; headers={}
        with patch.object(d.urllib.request,'urlopen',return_value=Response(data)):
            self.assertEqual(d.download(item,self.cache).read_bytes(),data)
    def test_bad_range(self):
        item=self.item(b'abcdef'); self.cache.mkdir()
        (self.cache/'bundle.zip.partial').write_bytes(b'abc')
        (self.cache/'bundle.zip.checkpoint.json').write_text(json.dumps({k:item[k] for k in ('name','bytes','sha256','url')}))
        class Response(io.BytesIO): status=206; headers={'Content-Range':'bytes 0-2/6'}
        with patch.object(d.urllib.request,'urlopen',return_value=Response(b'def')):
            with self.assertRaises(ValueError): d.download(item,self.cache)
    def test_idempotence_and_mismatch(self):
        path=self.zip([('a',b'abc'),('b',b'def')]); item=self.item(path.read_bytes()); target=self.root/'target'
        d.install(path,item,target,[]); d.install(path,item,target,[])
        (target/'a').write_bytes(b'bad'); (target/'b').unlink()
        with self.assertRaises(ValueError): d.install(path,item,target,[])
        self.assertFalse((target/'b').exists()); self.assertEqual((target/'a').read_bytes(),b'bad')
    def test_staged_manifest_mismatch(self):
        path=self.zip([('a',b'abc')]); item=self.item(path.read_bytes())
        record=dict(path='a',bytes=3,sha256='0'*64,package='website-core')
        with self.assertRaises(ValueError): d.install(path,item,self.root/'target',[record])
        self.assertFalse((self.root/'target/a').exists())
    def test_acceptance_before_download(self):
        item=self.item(b'abc'); item.update(id='replica-research',requires_acceptance='replica-research')
        manifest=self.root/'manifest.json'; manifest.write_text(json.dumps(dict(assets=[item],files=[])))
        with patch.object(d,'download') as download:
            with self.assertRaises(ValueError): d.main(['--manifest',str(manifest),'--package','replica-research'])
            download.assert_not_called()
    def test_rollback_on_move_failure(self):
        path=self.zip([('a',b'abc'),('b',b'def')]); original=d.os.replace; calls=[]
        def replace(a,b):
            calls.append(b)
            if len(calls)==2: raise OSError('simulated disk error')
            original(a,b)
        with patch.object(d.os,'replace',replace):
            with self.assertRaises(OSError): d.install(path,self.item(path.read_bytes()),self.root/'target',[])
        self.assertFalse((self.root/'target/a').exists())

if __name__=='__main__': unittest.main()
