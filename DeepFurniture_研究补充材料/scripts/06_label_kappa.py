#!/usr/bin/env python3
"""独立双标注者的Cohen κ统计；不代填原稿中的0.87和0.92。"""
import argparse,csv,json
from collections import Counter
from pathlib import Path

def kappa(a,b):
 if not a or len(a)!=len(b):raise ValueError('标注缺失或样本数不一致')
 n=len(a);observed=sum(x==y for x,y in zip(a,b))/n
 ca=Counter(a);cb=Counter(b)
 chance=sum((ca[k]/n)*(cb[k]/n) for k in set(ca)|set(cb))
 return (observed-chance)/(1-chance) if chance!=1 else 1.0

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--review',required=True,type=Path);p.add_argument('--out',required=True,type=Path);args=p.parse_args()
 with args.review.open(encoding='utf-8-sig',newline='') as f:rs=list(csv.DictReader(f))
 out={}
 for mode in ['style','category']:
  col1,col2='reviewer1_'+mode,'reviewer2_'+mode
  valid=[r for r in rs if r.get(col1,'').strip() and r.get(col2,'').strip()]
  if not valid:out[mode]={'n':0,'kappa':None,'status':'no_independent_review_records'}
  else:out[mode]={'n':len(valid),'kappa':round(kappa([r[col1] for r in valid],[r[col2] for r in valid]),6),'observed_agreement':round(sum(r[col1]==r[col2] for r in valid)/len(valid),6)}
 args.out.parent.mkdir(exist_ok=True,parents=True)
 args.out.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
