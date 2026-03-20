import os
import sys
import django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.conf.settings')
django.setup()

from evennia.utils.search import search_object
from evennia.utils.create import create_object
from typeclasses.exits import Exit

def restore():
    sq = search_object('Town Square')[0]
    tav = search_object('The Neural Tavern')[0]
    
    print(f"Square ID: {sq.id}, Tavern ID: {tav.id}")
    
    # Square -> Tavern
    existing = [ex for ex in sq.exits if ex.key.lower() in ['north', 'n', 'the neural tavern']]
    if not existing:
        create_object(Exit, key='North', aliases=['n', 'tavern', 'The Neural Tavern'], location=sq, destination=tav)
        print('Created North exit from Square to Tavern.')
    else:
        for ex in existing:
            ex.destination = tav
            print(f'Updated Square-Tavern exit {ex.key} to point to {tav.id}.')
            
    # Tavern -> Square
    existing_rev = [ex for ex in tav.exits if ex.key.lower() in ['south', 's', 'town square', 'square']]
    if not existing_rev:
        create_object(Exit, key='South', aliases=['s', 'square', 'Town Square'], location=tav, destination=sq)
        print('Created South exit from Tavern to Square.')
    else:
        for ex in existing_rev:
            ex.destination = sq
            print(f'Updated Tavern-Square exit {ex.key} to point to {sq.id}.')

if __name__ == "__main__":
    restore()
