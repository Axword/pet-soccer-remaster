"""Inert native opaque-BC1 TEX codec. Importing never reads/writes files.

Supported template:01afdabc, encoding1, power-of-two RGB, complete mip chain.
Reject other engine formats rather than guessing alpha/layout conventions.
"""
import io, struct
import numpy as np
from PIL import Image


def parse_tex(data):
    assert data[:4] == bytes.fromhex('01afdabc')
    encoding,w,h=struct.unpack_from('<3I',data,4)
    assert encoding==1 and 1<=w<=1024 and 1<=h<=1024
    assert w&(w-1)==0 and h&(h-1)==0
    chunks=[];pos=16
    for level in range(max(w,h).bit_length()):
        index,size=struct.unpack_from('<2I',data,pos);pos+=8
        expected=max(1,((max(1,w>>level)+3)//4))*max(1,((max(1,h>>level)+3)//4))*8
        assert index==level and size==expected and pos+size<=len(data)
        chunks.append(data[pos:pos+size]);pos+=size
    assert pos==len(data)
    return w,h,chunks


def decode_bc1(payload,size):
    return Image.frombytes('RGBA',size,payload,'bcn',(1,'DXT1')).convert('RGB')


def decode_level(data,level=0):
    w,h,chunks=parse_tex(data)
    assert 0<=level<len(chunks)
    return decode_bc1(chunks[level],(max(1,w>>level),max(1,h>>level)))


def encode_bc1(image,mean_rgb=None):
    if image.mode=='RGBA':assert image.getextrema()[3]==(255,255),'Opaque BC1 only'
    image=image.convert('RGB');size=image.size
    source=np.asarray(image,dtype=np.float32)
    offset=np.zeros(3,dtype=np.float32);best=None;best_error=float('inf')
    for attempt in range(4 if mean_rgb is not None else 1):
        adjusted=Image.fromarray(np.clip(np.rint(source+offset),0,255).astype(np.uint8),'RGB')
        encoded=adjusted
        if min(size)<4:encoded=adjusted.resize((max(4,size[0]),max(4,size[1])),Image.Resampling.NEAREST)
        stream=io.BytesIO();encoded.save(stream,format='DDS',pixel_format='DXT1')
        data=stream.getvalue();assert data[:4]==b'DDS ' and data[84:88]==b'DXT1'
        payload=data[128:]
        if mean_rgb is None:return payload
        actual=np.asarray(decode_bc1(payload,size),dtype=np.float32).mean((0,1))
        error=np.asarray(mean_rgb,dtype=np.float32)-actual
        score=float(np.abs(error).max())
        if score<best_error:best,best_error=payload,score
        if score<.35:break
        offset=np.clip(offset+error,-8,8)
    return best


def assemble_tex(template,chunks):
    w,h,original=parse_tex(template);assert len(chunks)==len(original)
    assert all(len(a)==len(b) for a,b in zip(original,chunks))
    result=template[:16]+b''.join(struct.pack('<II',i,len(c))+c for i,c in enumerate(chunks))
    parse_tex(result);assert len(result)==len(template)
    return result


def encode_tex(image,template):
    w,h,old=parse_tex(template);assert image.size==(w,h)
    if image.mode=='RGBA':assert image.getextrema()[3]==(255,255),'Opaque BC1 only'
    chunks=[]
    for level in range(len(old)):
        mip=image.convert('RGB') if level==0 else image.convert('RGB').resize((max(1,w>>level),max(1,h>>level)),Image.Resampling.LANCZOS)
        chunks.append(encode_bc1(mip))
    return assemble_tex(template,chunks)
