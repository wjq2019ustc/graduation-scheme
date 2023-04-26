a: dict = {'a':1}
b = a
b['b'] = 2
b['a'] = 0
print(a,b)
flag = b.get('c')
print(flag)

f = False
print(f)
if f:
    print(f)

c = a['a']
c -= 1
print(c, a)

print("ceffe", 10 % 10)