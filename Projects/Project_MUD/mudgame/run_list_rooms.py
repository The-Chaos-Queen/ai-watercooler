import os
import sys
import django
import traceback

# Add the project directory to sys.path so we can import modules
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Set the Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

# Setup Django
try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    traceback.print_exc()
    sys.exit(1)

# Now import and run the check_room script
try:
    import list_rooms
except ImportError:
    print("Error: Could not import list_rooms.")
    traceback.print_exc()
except Exception as e:
    print(f"Error running list_rooms script: {e}")
    traceback.print_exc()
