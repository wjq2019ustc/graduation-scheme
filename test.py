a: dict = {'a':1}
b = a
b['b'] = 2
print(a,b)
flag = b.get('c')
print(flag)

f = False
print(f)
if f:
    print(f)