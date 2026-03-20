import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

try:
    import evennia
    print("Evennia import successful")
    from evennia.objects.models import ObjectDB
    print(f"Room count: {ObjectDB.objects.filter(db_typeclass_path__icontains='room').count()}")
except ImportError as e:
    print(f"Import failed: {e}")
