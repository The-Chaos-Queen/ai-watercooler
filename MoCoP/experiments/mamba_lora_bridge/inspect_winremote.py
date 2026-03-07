import winremote

print(dir(winremote))
import os
print(os.listdir(os.path.dirname(winremote.__file__)))
