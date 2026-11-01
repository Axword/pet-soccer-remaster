"""Small Java1.3 class-file editing helpers. No file I/O on import."""
import struct

U2=lambda x:struct.pack('>H',x)
U4=lambda x:struct.pack('>I',x)
class ClassFile:
 def __init__(self,b):
  self.head=b[:8];self.cp=[None];p=10
  def u2():
   nonlocal p
   x=struct.unpack_from('>H',b,p)[0];p+=2;return x
  count=struct.unpack_from('>H',b,8)[0]
  while len(self.cp)<count:
   start=p;t=b[p];p+=1
   if t==1:n=u2();v=b[p:p+n].decode('utf8');p+=n
   elif t in (7,8):v=u2()
   elif t in (9,10,11,12):v=(u2(),u2())
   elif t in (3,4):v=b[p:p+4];p+=4
   elif t in (5,6):v=b[p:p+8];p+=8
   else:raise ValueError(t)
   self.cp.append((t,v,b[start:p]))
   if t in (5,6):self.cp.append(None)
  self.bodyhead=b[p:p+6];p+=6
  n=u2();self.interfaces=U2(n)+b[p:p+n*2];p+=n*2
  def attrs():
   nonlocal p
   a=[]
   for _ in range(u2()):
    name=u2();n=struct.unpack_from('>I',b,p)[0];p+=4;a.append([name,b[p:p+n]]);p+=n
   return a
  def members():
   a=[]
   for _ in range(u2()):
    flags,name,desc=u2(),u2(),u2();a.append([flags,name,desc,attrs()])
   return a
  self.fields=members();self.methods=members();self.attrs=attrs();assert p==len(b)
 def ref(self,i):
  t,v,_=self.cp[i]
  if t==1:return v
  if t in (7,8):return self.ref(v)
  if t in (9,10,11,12):return self.ref(v[0])+'.'+self.ref(v[1])
  return str(v)
 def add(self,t,v):
  for i,c in enumerate(self.cp):
   if c and c[:2]==(t,v):return i
  data=bytes([t])+(U2(len(v.encode()))+v.encode() if t==1 else U2(v) if t in (7,8) else U2(v[0])+U2(v[1]))
  self.cp.append((t,v,data));return len(self.cp)-1
 def clazz(self,s):return self.add(7,self.add(1,s))
 def string(self,s):return self.add(8,self.add(1,s))
 def member(self,owner,name,desc,t=9):return self.add(t,(self.clazz(owner),self.add(12,(self.add(1,name),self.add(1,desc)))))
 def code(self,name,desc=None):
  m=next(m for m in self.methods if self.ref(m[1])==name and (desc is None or self.ref(m[2])==desc))
  return next(a for a in m[3] if self.ref(a[0])=='Code')
 def edit(self,name,fn,desc=None):
  a=self.code(name,desc);b=a[1];stack,locals,n=struct.unpack_from('>HHI',b);code=bytearray(b[8:8+n]);tail=b[8+n:]
  code=bytes(fn(code));assert tail[:2]==b'\0\0','exception handlers need relocation'
  # Drop debug-only nested attributes so code size changes cannot stale offsets.
  a[1]=struct.pack('>HHI',max(16,stack),locals,len(code))+code+b'\0\0\0\0'
 def emit(self):
  def attrs(a):return U2(len(a))+b''.join(U2(n)+U4(len(v))+v for n,v in a)
  def members(a):return U2(len(a))+b''.join(U2(f)+U2(n)+U2(d)+attrs(at) for f,n,d,at in a)
  return self.head+U2(len(self.cp))+b''.join(c[2] for c in self.cp[1:] if c)+self.bodyhead+self.interfaces+members(self.fields)+members(self.methods)+attrs(self.attrs)
def op(n,i):return bytes([n])+U2(i)
def append(c,extra):assert c[-1]==177;return c[:-1]+extra+b'\xb1'
