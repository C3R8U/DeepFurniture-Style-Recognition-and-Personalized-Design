#!/usr/bin/env python3
"""把已核验的真实家具样本处理成224分类图、256生成图、主体掩码和256点轮廓。"""
import argparse,csv,json
from pathlib import Path
import cv2,numpy as np

def decode_segmentation(seg,height,width):
 """官方场景实例分割为COCO RLE；不支持的标注不静默伪造成精确掩码。"""
 if seg is None:return None
 try:
  from pycocotools import mask as mask_utils
  obj=seg
  if isinstance(seg,list) and all(isinstance(v,(int,float)) for v in seg):
   obj={'size':[height,width],'counts':[int(v) for v in seg]}
  if isinstance(obj,dict) and isinstance(obj.get('counts'),list):
   obj=mask_utils.frPyObjects(obj,height,width)
  if isinstance(obj,dict) and isinstance(obj.get('counts'),str):
   obj={**obj,'counts':obj['counts'].encode('ascii')}
  dec=mask_utils.decode(obj)
  if dec.ndim==3:dec=np.max(dec,axis=2)
  if dec.shape!=(height,width):return None
  return np.asarray(dec>0,np.uint8)*255
 except (ImportError,ValueError,TypeError,KeyError,OverflowError):return None

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--root',required=True,type=Path)
 ap.add_argument('--split-file',required=True,type=Path)
 ap.add_argument('--output-dir',required=True,type=Path)
 ap.add_argument('--allow-bbox-fallback',action='store_true',help='仅用于调试；不适合作为原研究分割掩码')
 args=ap.parse_args();root=args.root.resolve();out=args.output_dir;out.mkdir(parents=True,exist_ok=True)
 log=[];total=0
 with args.split_file.open(encoding='utf-8-sig',newline='') as f:
  for row in csv.DictReader(f):
   sid=row['sample_id'];split=row['split']
   scene=cv2.imread(str(root/row['scene_image']))
   if scene is None:raise RuntimeError(f'{sid} 缺少图像 {row["scene_image"]}')
   ann=json.loads((root/row['scene_annotation']).read_text(encoding='utf8'))
   inst=ann['instances'][int(row['instance_index'])]
   fullmask=decode_segmentation(inst.get('segmentation'),scene.shape[0],scene.shape[1]);mask_source='instance_segmentation'
   x0,y0,x1,y1=map(int,row['bbox'].split(','))
   x0=max(0,min(x0,scene.shape[1]-1));y0=max(0,min(y0,scene.shape[0]-1));x1=max(x0+1,min(x1,scene.shape[1]));y1=max(y0+1,min(y1,scene.shape[0]))
   if fullmask is None:
    if not args.allow_bbox_fallback:raise RuntimeError(f'{sid} RLE分割不可用，终止。避免将bbox当真实实例掩码。')
    fullmask=np.zeros(scene.shape[:2],np.uint8);fullmask[y0:y1,x0:x1]=255;mask_source='bbox_fallback_DEBUG_ONLY'
   crop=scene[y0:y1,x0:x1];mask=fullmask[y0:y1,x0:x1]
   n,labels,stats,_=cv2.connectedComponentsWithStats(np.uint8(mask>0),8)
   if n<=1:raise RuntimeError(f'{sid} 无有效分割前景')
   keep=1+np.argmax(stats[1:,cv2.CC_STAT_AREA]);mask=np.uint8(labels==keep)*255
   foreground=cv2.bitwise_and(crop,crop,mask=mask)
   rgb256=cv2.resize(foreground,(256,256),interpolation=cv2.INTER_AREA)
   mask256=cv2.resize(mask,(256,256),interpolation=cv2.INTER_NEAREST)
   rgb224=rgb256[16:240,16:240]
   edges=cv2.Canny(mask256,60,160)
   contours,_=cv2.findContours(edges,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
   if not contours:raise RuntimeError(f'{sid} 提取轮廓失败')
   contour=max(contours,key=cv2.arcLength).reshape(-1,2).astype(np.float64)
   closed=np.vstack([contour,contour[0]]); seg=np.linalg.norm(np.diff(closed,axis=0),axis=1)
   cum=np.concatenate([[0],np.cumsum(seg)])
   if cum[-1]<1:raise RuntimeError('轮廓长度为零')
   arc=np.linspace(0,cum[-1],256,endpoint=False)
   coords=np.stack([np.interp(arc,cum,closed[:,0]),np.interp(arc,cum,closed[:,1])],axis=1).astype(np.float32)
   where=out/split
   for folder in ['classification_224','generation_256','mask_256','contour_256']:(where/folder).mkdir(exist_ok=True,parents=True)
   cv2.imwrite(str(where/'classification_224'/f'{sid}.png'),rgb224)
   cv2.imwrite(str(where/'generation_256'/f'{sid}.png'),rgb256)
   cv2.imwrite(str(where/'mask_256'/f'{sid}.png'),mask256)
   np.save(where/'contour_256'/f'{sid}.npy',coords)
   log.append(dict(sample_id=sid,split=split,mask_source=mask_source,contour_points=256,preprocess_status='ok'))
   total+=1
 logfile=out/'preprocessing_provenance.csv'
 with logfile.open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=['sample_id','split','mask_source','contour_points','preprocess_status']);w.writeheader();w.writerows(log)
 print('处理完成',total,'样本；日志',logfile)
if __name__=='__main__':main()
