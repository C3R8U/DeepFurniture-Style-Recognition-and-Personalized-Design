#!/usr/bin/env python3
"""计算真实候选图像的64位pHash，并列出汉明距离<=8的近重复对供人工核验。"""
import argparse,csv,hashlib,json,sys
from collections import defaultdict
from pathlib import Path
import cv2
import numpy as np

def phash64(image):
 gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
 sm=cv2.resize(gray,(32,32),interpolation=cv2.INTER_AREA).astype(np.float32)
 dct=cv2.dct(sm)[:8,:8]; threshold=np.median(dct.flatten()[1:])
 bits=(dct>=threshold).reshape(-1)
 result=0
 for v in bits:result=(result<<1)|int(v)
 return result

def hamming(a,b):return (a^b).bit_count()
class BKNode:
 def __init__(self,val,sid):self.val=val;self.sids=[sid];self.children={}
class BKTree:
 def __init__(self):self.root=None
 def add(self,val,sid):
  if self.root is None:self.root=BKNode(val,sid);return
  node=self.root
  while True:
   dist=hamming(val,node.val)
   if dist==0:node.sids.append(sid);return
   nxt=node.children.get(dist)
   if nxt is None:node.children[dist]=BKNode(val,sid);return
   node=nxt
 def search(self,val,maxdist):
  out=[];todo=[self.root] if self.root else []
  while todo:
   node=todo.pop();d=hamming(val,node.val)
   if d<=maxdist:out.extend((sid,d) for sid in node.sids)
   lo=max(d-maxdist,1);hi=d+maxdist
   todo.extend(child for diff,child in node.children.items() if lo<=diff<=hi)
  return out

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--root',type=Path,required=True)
 p.add_argument('--inventory',type=Path,required=True)
 p.add_argument('--review',type=Path,required=True)
 p.add_argument('--out-dir',type=Path,required=True)
 p.add_argument('--threshold',type=int,default=8)
 args=p.parse_args();root=args.root.resolve();out=args.out_dir;out.mkdir(parents=True,exist_ok=True)
 with args.review.open(encoding='utf-8-sig',newline='') as f:
  approved={r['sample_id'] for r in csv.DictReader(f) if r.get('decision','').strip().lower()=='approved'}
 fields=['sample_id','identity_id','style','category','pHash64_hex','image_source','compute_status']
 pairs_fields=['sample_id_1','sample_id_2','identity_id_1','identity_id_2','hamming','same_identity','recommended_review_action']
 records=[];pairs=[];tree=BKTree();data={}
 with args.inventory.open(encoding='utf-8-sig',newline='') as f:
  for r in csv.DictReader(f):
   sid=r['sample_id']
   if sid not in approved:continue
   imagefile=root/r['scene_image']
   if not imagefile.exists():raise FileNotFoundError(imagefile)
   im=cv2.imread(str(imagefile))
   if im is None:raise RuntimeError('图像解码失败: '+str(imagefile))
   try:
    x0,y0,x1,y1=[int(r[k]) for k in ('x_min','y_min','x_max','y_max')]
    x0=max(0,min(x0,im.shape[1]-1));x1=max(x0+1,min(x1,im.shape[1]));y0=max(0,min(y0,im.shape[0]-1));y1=max(y0+1,min(y1,im.shape[0]))
    crop=im[y0:y1,x0:x1]
    if crop.size==0:raise ValueError('invalid crop')
    ph=phash64(crop)
   except Exception as exc:raise RuntimeError(f'{sid} 哈希计算错误') from exc
   for psid,d in tree.search(ph,args.threshold):
    prior=data[psid]
    pairs.append(dict(sample_id_1=psid,sample_id_2=sid,identity_id_1=prior['identity_id'],identity_id_2=r['identity_id'],hamming=d,same_identity=str(prior['identity_id']==r['identity_id']),recommended_review_action='keep_one_after_visual_confirmation'))
   tree.add(ph,sid);data[sid]=r
   records.append(dict(sample_id=sid,identity_id=r['identity_id'],style=r['candidate_style'],category=r['candidate_category'],pHash64_hex=f'{ph:016x}',image_source=r['scene_image'],compute_status='ok'))
 for fname,fn,rows in [('phashes.csv',fields,records),('near_duplicate_pairs_review.csv',pairs_fields,pairs)]:
  with (out/fname).open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.DictWriter(f,fieldnames=fn);w.writeheader();w.writerows(rows)
 print(json.dumps({'hashed_images':len(records),'pairs_at_or_below_threshold':len(pairs),'threshold':args.threshold,'out_dir':str(out)},ensure_ascii=False))
 print('请人工检查 near_duplicate_pairs_review.csv；若确认近重复，修改 review.csv 的 decision 为 rejected，之后重新划分。')
if __name__=='__main__':main()
