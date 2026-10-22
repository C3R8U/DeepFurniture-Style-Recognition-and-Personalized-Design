#!/usr/bin/env python3
"""从 DeepFurniture 官方解压目录提取真实家具实例索引，不生成虚构编号。"""
import argparse,csv,hashlib,json,sys
from collections import Counter
from pathlib import Path

FIELDS=['sample_id','scene_id','instance_index','instance_number','identity_id','raw_category_id','raw_category','raw_style_ids','raw_styles','candidate_category','candidate_style','mapping_issue','scene_image','scene_annotation','x_min','y_min','x_max','y_max','scene_group']
STYLE_MAP={'1':'Modern','3':'American','4':'Chinese','8':'Nordic','9':'Industrial'}
CATEGORY_MAP={'1':'Cabinet','2':'Table','3':'Chair','4':'Lamp','7':'Sofa'}

def as_id(x):
    try: return str(int(x))
    except (ValueError,TypeError): return str(x)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--root',type=Path,required=True,help='官方 uncompress_dataset.sh 的输出目录')
 p.add_argument('--output',type=Path,required=True)
 args=p.parse_args()
 root=args.root.resolve(); scene_root=root/'scenes'; metadata=root/'metadata'
 if not scene_root.is_dir(): p.error(f'找不到 scenes 目录: {scene_root}')
 if not (metadata/'styles.json').exists(): p.error(f'找不到原始 metadata/styles.json: {metadata}')
 args.output.parent.mkdir(parents=True,exist_ok=True)
 counts=Counter()
 with args.output.open('w',encoding='utf-8-sig',newline='') as out:
  writer=csv.DictWriter(out,fieldnames=FIELDS);writer.writeheader()
  for ann in sorted(scene_root.glob('*/annotation.json')):
   scene_id=ann.parent.name
   image=ann.parent/'image.jpg'
   if not image.is_file():counts['scene_image_missing']+=1;continue
   try:
    data=json.loads(ann.read_text(encoding='utf-8')); instances=data.get('instances',[])
   except (OSError,ValueError):counts['annotation_invalid']+=1;continue
   for idx,inst in enumerate(instances):
    catid=as_id(inst.get('categoryID',''))
    if catid not in CATEGORY_MAP: counts['category_outside_target']+=1;continue
    styleids=sorted(set(as_id(v) for v in inst.get('styleIDs',[])))
    target_styles=sorted(set(STYLE_MAP[s] for s in styleids if s in STYLE_MAP))
    # 只有原始标签恰有一个目标风格时才给出候选；仍然必须人工核验。
    candidate_style=target_styles[0] if len(target_styles)==1 else ''
    issue='REVIEW_REQUIRED'
    if len(target_styles)!=1: issue='AMBIGUOUS_OR_UNKNOWN_STYLE'
    if len(styleids)>1: issue+=';MULTI_LABEL'
    ident=as_id(inst.get('identityID',''))
    if not ident: counts['identity_missing']+=1;continue
    box=inst.get('boundingBox',{})
    try:
     coords=[int(box[x]) for x in ('xMin','yMin','xMax','yMax')]
     if coords[2]<=coords[0] or coords[3]<=coords[1]:raise ValueError('empty bounding box')
    except (ValueError,KeyError,TypeError):counts['bbox_invalid']+=1;continue
    rawstyles=inst.get('styleNames',[])
    sid=hashlib.sha256(f'{scene_id}|{idx}|{ident}'.encode('utf8')).hexdigest()[:20]
    writer.writerow(dict(sample_id=sid,scene_id=scene_id,instance_index=idx,instance_number=inst.get('numberID',''),identity_id=ident,raw_category_id=catid,raw_category=inst.get('categoryName',''),raw_style_ids='|'.join(styleids),raw_styles='|'.join(map(str,rawstyles)),candidate_category=CATEGORY_MAP[catid],candidate_style=candidate_style,mapping_issue=issue,scene_image=str(image.relative_to(root)),scene_annotation=str(ann.relative_to(root)),x_min=coords[0],y_min=coords[1],x_max=coords[2],y_max=coords[3],scene_group=scene_id))
    counts['candidate_rows']+=1
    if candidate_style:counts['candidate_with_style']+=1
    else:counts['candidate_needs_style_mapping']+=1
 print(json.dumps({'dataset_root':str(root),'inventory_csv':str(args.output),'counts':dict(counts)},ensure_ascii=False,indent=2))
 if not counts['candidate_rows']:sys.exit('没有提取到有效家具实例；请检查官方解压目录。')
if __name__=='__main__':main()
