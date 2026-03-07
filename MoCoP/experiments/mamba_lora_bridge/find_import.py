import pkgutil

print("Looking for winremote packages...")
found = []
for m in pkgutil.iter_modules():
    if getattr(m, 'name', None):
        if 'winremote' in m.name:
            found.append(m.name)
    elif len(m) > 1 and 'winremote' in m[1]:
        found.append(m[1])
print("Found:", found)
