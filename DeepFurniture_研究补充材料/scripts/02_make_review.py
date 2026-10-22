#!/usr/bin/env python3
"""从原始样本索引生成双人核验表，禁止自动宣称五种目标风格标签已确认。"""
import argparse,csv
from pathlib import Path
FIELDS=['sample_id','identity_id','scene_id','candidate_style','candidate_category','reviewer1_style','reviewer2_style','reviewer1_category','reviewer2_category','adjudicated_style','adjudicated_category','decision','decision_reason','reviewer_notes']
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--inventory',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);args=ap.parse_args()
 args.output.parent.mkdir(parents=True,exist_ok=True)
 with args.inventory.open(encoding='utf-8-sig',newline='') as fi,args.output.open('w',encoding='utf-8-sig',newline='') as fo:
  w=csv.DictWriter(fo,fieldnames=FIELDS);w.writeheader()
  for r in csv.DictReader(fi):
   w.writerow({**{k:r.get(k,'') for k in FIELDS},'decision':'pending'})
 print('核验表已生成：',args.output)
 print('人工核验完成后，填写 reviewer1/2、adjudicated_* 和 decision=approved/rejected。')
if __name__=='__main__':main()
