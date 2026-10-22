#!/usr/bin/env python3
"""将真实且已复核的家具索引生成平衡 5×5×500 数据划分；不足时失败，不补造记录。"""
import argparse,csv,hashlib,json,sys
from collections import Counter,defaultdict
from pathlib import Path

STYLES=['Modern','Nordic','Chinese','Industrial','American']
CATEGORIES=['Chair','Table','Sofa','Cabinet','Lamp']
SPLITS={'train':350,'validation':75,'test':75}
OUT_FIELDS=['sample_id','identity_id','scene_id','instance_index','target_style','target_category','split','scene_image','scene_annotation','bbox','raw_style_ids','raw_category_id','label_source','review_decision','group_id']

def readcsv(path):
 with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def bucket(group,seed):
 n=int(hashlib.sha256(f'{seed}|{group}'.encode()).hexdigest()[:14],16)%10000
 return 'train' if n<7000 else ('validation' if n<8500 else 'test')

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--inventory',required=True,type=Path)
 ap.add_argument('--review',required=True,type=Path)
 ap.add_argument('--output',required=True,type=Path)
 ap.add_argument('--seed',type=int,default=2024)
 ap.add_argument('--counts-only',action='store_true')
 ap.add_argument('--near-duplicate-pairs',type=Path,help='02b脚本输出的近重复核验列表，正式发布时必须提供')
 args=ap.parse_args()
 inventory={r['sample_id']:r for r in readcsv(args.inventory)}
 approved={}; stats=Counter(); reviews=readcsv(args.review)
 for rr in reviews:
  sid=rr.get('sample_id','')
  if sid not in inventory: raise ValueError('核验结果中含未知 sample_id: '+sid)
  if sid in approved:raise ValueError('同一 sample_id 重复核验: '+sid)
  dec=rr.get('decision','').strip().lower()
  stats[dec or 'missing_decision']+=1
  if dec!='approved':continue
  # approved 必须包含两人标签和最终确认；不允许从候选标签自动继承。
  for f in ('reviewer1_style','reviewer2_style','reviewer1_category','reviewer2_category','adjudicated_style','adjudicated_category'):
   if not rr.get(f,'').strip():raise ValueError(f'已批准的样本 {sid} 缺少 {f}')
  style=rr['adjudicated_style'].strip();cat=rr['adjudicated_category'].strip()
  if style not in STYLES or cat not in CATEGORIES: raise ValueError(f'{sid} 类别不属于目标标签: {style}/{cat}')
  approved[sid]=(style,cat)
  # 样本ID映射至元数据中真实的身份，不用随机生成的身份进行产品分组。
 print('核验状态汇总:',dict(stats),'批准条数:',len(approved))
 cells=defaultdict(list)
 for sid,(style,cat) in approved.items():
  row=inventory[sid];identity=row['identity_id']
  if not identity:raise ValueError('缺失家具身份ID')
  key=(style,cat,bucket(identity,args.seed))
  cells[key].append(row)
 short=[]
 for style in STYLES:
  for cat in CATEGORIES:
   for split,need in SPLITS.items():
    have=len(cells[(style,cat,split)])
    if have<need:short.append({'style':style,'category':cat,'split':split,'required':need,'available':have})
 report=args.output.with_suffix('.availability.json')
 report.parent.mkdir(parents=True,exist_ok=True)
 report.write_text(json.dumps({'source':'real approved inventory only','seed':args.seed,'counts':dict(stats),'insufficient_cells':short},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 if args.counts_only:return
 if args.near_duplicate_pairs is None:ap.error('正式生成训练划分必须提供 --near-duplicate-pairs，确认近重复检测已经完成')
 with args.near_duplicate_pairs.open(encoding='utf-8-sig',newline='') as f:
  unresolved=[r for r in csv.DictReader(f) if r.get('sample_id_1') in approved and r.get('sample_id_2') in approved]
 if unresolved: raise RuntimeError(f'存在 {len(unresolved)} 对仍同时获批准的近重复图像，请人工复核并将一方标为 rejected，再重新运行02b')
 if short:
  print('样本不足或核验尚未完成，未创建正式划分文件。详细不足项:',report,file=sys.stderr)
  for r in short[:15]:print(r,file=sys.stderr)
  sys.exit(2)
 result=[]
 for style in STYLES:
  for cat in CATEGORIES:
   for split,need in SPLITS.items():
    arr=cells[(style,cat,split)]
    # 稳定排序，避免不同系统的文件扫描顺序影响结果
    arr.sort(key=lambda r:hashlib.sha256(f"{args.seed}|{r['sample_id']}".encode()).hexdigest())
    for r in arr[:need]:
     result.append({'sample_id':r['sample_id'],'identity_id':r['identity_id'],'scene_id':r['scene_id'],'instance_index':r['instance_index'],'target_style':style,'target_category':cat,'split':split,'scene_image':r['scene_image'],'scene_annotation':r['scene_annotation'],'bbox':','.join(r[k] for k in ('x_min','y_min','x_max','y_max')),'raw_style_ids':r['raw_style_ids'],'raw_category_id':r['raw_category_id'],'label_source':'two_reviewers_adjudicated','review_decision':'approved','group_id':r['identity_id']})
 with args.output.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=OUT_FIELDS);w.writeheader();w.writerows(result)
 for split in SPLITS:
  with args.output.with_name(f'{split}.csv').open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.DictWriter(f,fieldnames=OUT_FIELDS);w.writeheader();w.writerows([r for r in result if r['split']==split])
 print('真实样本划分已写入:',args.output,'总计',len(result))
 print('注意：近重复去除与轮廓处理还需按预处理脚本执行；划分前的去重审核结果应回写核验表。')
if __name__=='__main__':main()
