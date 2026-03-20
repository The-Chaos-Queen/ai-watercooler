import re
from evennia import search_object

def generate_aliases(name):
    """
    Generate aliases like "neural tavern", "tavern" from "The Neural Tavern".
    """
    aliases = set()
    name = str(name).strip()
    lower_name = name.lower()
    aliases.add(lower_name)
    
    # Remove 'the ', 'a ', 'an '
    stripped = re.sub(r'^(the|a|an)\s+', '', lower_name)
    if stripped and stripped != lower_name:
         aliases.add(stripped)
         
    # Add individual words if there are multiple
    words = stripped.split()
    if len(words) > 1:
         for word in words:
             # Exclude tiny words
             if len(word) > 2 and word not in ['and', 'of', 'in', 'on', 'at', 'to']:
                 aliases.add(word)
                 
    # Try to make a very short acronym if > 2 words? Optional.
    return list(aliases)

def main():
    exits = search_object(typeclass="evennia.objects.objects.DefaultExit")
    # Also find subclasses like our custom Exits if any
    all_exits = []
    from evennia.objects.models import ObjectDB
    for obj in ObjectDB.objects.all():
        if obj.destination:
            all_exits.append(obj)
            
    modified = 0
    for ex in all_exits:
        if not ex.destination:
            continue
            
        dest_name = ex.destination.key
        
        # Don't rename if it's already named after the destination somehow perfectly, 
        # but let's just force update all exits to match the destination name.
        old_name = ex.key
        ex.key = dest_name
        
        # Build aliases
        current_aliases = ex.aliases.all()
        new_aliases = generate_aliases(dest_name)
        
        # Clear old aliases like "north", "south", etc.
        ex.aliases.clear()
        
        # Add new aliases
        for al in new_aliases:
            ex.aliases.add(al)
            
        print(f"Updated exit [Old: {old_name}] -> [New: {ex.key}], Aliases: {new_aliases}")
        modified += 1
        
    print(f"Finished updating {modified} exits.")

if __name__ == "__main__":
    main()
