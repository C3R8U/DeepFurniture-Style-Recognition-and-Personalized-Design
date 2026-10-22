"""仅用测试数据核查代码，不属于论文的真实家具样本。"""
import importlib.util,sys,unittest
from pathlib import Path
SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
def load(name,filename):
 spec=importlib.util.spec_from_file_location(name,SCRIPTS/filename)
 mod=importlib.util.module_from_spec(spec)
 spec.loader.exec_module(mod)
 return mod
class TestSupplementTools(unittest.TestCase):
 def test_kappa(self):
  k=load('m06','06_label_kappa.py').kappa
  self.assertAlmostEqual(k(['a','a','b','b'],['a','a','b','b']),1.0)
  self.assertAlmostEqual(k(['a','a','b','b'],['a','b','a','b']),0.0)
 def test_bk_tree_hamming(self):
  m=load('m02b','02b_duplicate_audit.py')
  t=m.BKTree();t.add(0,'a');t.add(255,'b');t.add(1<<25,'c')
  self.assertIn(('a',1),t.search(1,1))
  self.assertNotIn(('b',8),t.search(1,1))
 def test_hash_split_stable(self):
  m=load('m03','03_build_splits.py')
  a=m.bucket('genuine_identity_001',2024)
  self.assertEqual(a,m.bucket('genuine_identity_001',2024))
  self.assertIn(a,{'train','validation','test'})
 def test_original_label_scope(self):
  import json
  meta=Path(__file__).resolve().parents[1]/'source_metadata'
  styles=json.loads((meta/'styles.json').read_text())
  cats=json.loads((meta/'categories.json').read_text())
  self.assertEqual(len(styles),11)
  self.assertEqual(len(cats),11)
  self.assertEqual(styles['3'],'European#American')
  self.assertEqual(cats['3'],'chair#stool')
if __name__=='__main__':unittest.main()
