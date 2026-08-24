import hashlib
c="0D0B96E731C87025AF365109867DF6D9D74C5F79"
n1=int(c[0],16)
i=0
while i<2000000:
    s=hashlib.sha1((c+str(i)).encode()).digest()
    if s[n1]==0xb0 and s[n1+1]==0x0b:
        print(c+str(i)); break
    i+=1
