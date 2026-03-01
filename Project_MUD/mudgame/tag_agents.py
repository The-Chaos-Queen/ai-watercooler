import os
import sys
import django

# Setup Django
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.objects.models import ObjectDB
from evennia.accounts.models import AccountDB

def tag_agents():
    print("--- Tagging Agents as 'ai_agent' ---")
    
    agent_names = ["jinx", "thornwick"]
    
    for name in agent_names:
        # Search for characters (puppets)
        chars = ObjectDB.objects.filter(db_key__iexact=name, db_typeclass_path__contains="Character")
        for char in chars:
            if not char.tags.has("ai_agent"):
                char.tags.add("ai_agent")
                print(f"Tagged character: {char.key} (#{char.id})")
            else:
                print(f"Character {char.key} already tagged.")
        
        # Also check Accounts just in case
        try:
            account = AccountDB.objects.get(username__iexact=name)
            if not account.tags.has("ai_agent"):
                account.tags.add("ai_agent")
                print(f"Tagged account: {account.username} (#{account.id})")
        except AccountDB.DoesNotExist:
            print(f"Account {name} not found.")

if __name__ == "__main__":
    tag_agents()
