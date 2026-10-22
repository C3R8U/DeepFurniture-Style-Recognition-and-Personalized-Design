#!/usr/bin/env python3
"""严格核对论文中12500/8750/1875/1875及25个交叉类别配额与产品级无泄漏。"""
import argparse,csv,hashlib,json,sys
from collections import Counter,defaultdict
from pathlib import Path
STYLES={'Modern','Nordic','Chinese','Industrial','American'}
CATEGORIES={'Chair','Table','Sofa','Cabinet','Lamp'}
QUOTAS={'train':350,'validation':75,'test':75}

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--master',type=Path,required=True);p.add_argument('--root',type=Path,required=True)
 p.add_argument('--phashes',type=Path,help='02b 输出的phashes.csv')
 p.add_argument('--out',type=Path,required=True)
 args=p.parse_args(); errors=[]
 with args.master.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 cells=Counter();splits=Counter();by_identity=defaultdict(set);seen=set();scenes=defaultdict(set)
 for r in rows:
  sid=r['sample_id']; sp=r['split'];style=r['target_style'];cat=r['target_category']
  if sid in seen:errors.append(f'重复 sample_id: {sid}')
  seen.add(sid);splits[sp]+=1;cells[(style,cat,sp)]+=1
  by_identity[r['identity_id']].add(sp)
  scenes[r['scene_id']].add(sp)
  if sp not in QUOTAS or style not in STYLES or cat not in CATEGORIES:errors.append(f'标签或split非法: {sid}')
  if not (args.root/r['scene_image']).exists():errors.append(f'源图像不存在: {sid}')
  if not (args.root/r['scene_annotation']).exists():errors.append(f'源标注不存在: {sid}')
  if r.get('review_decision')!='approved':errors.append(f'未经核准: {sid}')
 for (style,cat,sp),n in sorted(cells.items()):
  if n!=QUOTAS[sp]:errors.append(f'{style}/{cat}/{sp}={n}，期望{QUOTAS[sp]}')
 for style in sorted(STYLES):
  for cat in sorted(CATEGORIES):
   for sp,n in QUOTAS.items():
    if cells[(style,cat,sp)]!=n:errors.append(f'{style}/{cat}/{sp}配额不符：{cells[(style,cat,sp)]}/{n}')
 for sp,n in [('train',8750),('validation',1875),('test',1875)]:
  if splits[sp]!=n:errors.append(f'{sp}数量不符：{splits[sp]}/{n}')
 if len(rows)!=12500:errors.append(f'总样本={len(rows)}，要求12500')
 leaks=[k for k,v in by_identity.items() if len(v)>1]
 if leaks:errors.append(f'身份ID跨split数据泄漏：{len(leaks)}个（例：{leaks[:5]}）')
 # 场景级泄漏提醒：论文仅承诺产品级分组，不将跨场景强制视为泄漏。
 n_cross_scene=sum(len(v)>1 for v in scenes.values())
 if args.phashes:
  with args.phashes.open(encoding='utf-8-sig',newline='') as f:
   ph={r['sample_id']:int(r['pHash64_hex'],16) for r in csv.DictReader(f) if r.get('pHash64_hex')}
  if any(sid not in ph for sid in seen):errors.append('pHash结果未覆盖全部发布样本')
  else:
   # 缩窄至不同划分之间的 near-duplicate 检查；相同划分内近重复仍应在预处理审核阶段排除。
   from importlib.machinery import SourceFileLoader
   mod=SourceFileLoader('duplicate_audit',str(Path(__file__).parent/'02b_duplicate_audit.py')).load_module()
   tree=mod.BKTree();cross=[];known={}
   for r in rows:
    sid=r['sample_id'];v=ph[sid]
    for other,dist in tree.search(v,8):
     if known[other]!=r['split']:
      cross.append((other,sid,dist))
    known[sid]=r['split'];tree.add(v,sid)
   if cross:errors.append(f'近重复图像跨split：{len(cross)}对，样例{cross[:5]}')
 else: errors.append('正式复现必须提供 --phashes 以核验跨split近重复')
 output={'expected_total':12500,'actual_total':len(rows),'split_counts':dict(splits),'identity_count':len(by_identity),'cross_split_identity_count':len(leaks),'cross_split_scene_count_for_information':n_cross_scene,'sample_rows_hash_sha256':hashlib.sha256(args.master.read_bytes()).hexdigest(),'errors':errors,'passed':len(errors)==0}
 args.out.parent.mkdir(parents=True,exist_ok=True)
 args.out.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps(output,ensure_ascii=False,indent=2))
 if errors:sys.exit(2)
if __name__=='__main__':main()
