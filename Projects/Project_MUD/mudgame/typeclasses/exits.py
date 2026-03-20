"""
Exits

Exits are connectors between Rooms. An exit always has a destination property
set and has a single command defined on itself with the same name as its key,
for allowing Characters to traverse the exit to its destination.

"""

from evennia.objects.objects import DefaultExit

from .objects import ObjectParent


class Exit(ObjectParent, DefaultExit):
    """
    Exits are connectors between rooms. Exits are normal Objects except
    they defines the `destination` property and overrides some hooks
    and methods to represent the exits.
    """
    def at_traverse(self, traversing_object, target_location, **kwargs):
        """
        Implements the actual traversal, checking for weather effects like slipping.
        """
        is_outdoor = self.location and self.location.tags.has("outdoor", category="environment")
        
        if is_outdoor:
            from evennia.utils.search import search_script
            scripts = search_script("global_weather")
            if scripts:
                weather = scripts[0]
                if weather.db.weather_state == "Data Rain":
                    import random
                    if random.random() < 0.2:  # 20% chance to slip!
                        traversing_object.msg("|yYou slip on the cascading data rain and fail to move!|n")
                        if self.location:
                            self.location.msg_contents(
                                f"{traversing_object.name} slips on the data rain and falls!",
                                exclude=traversing_object
                            )
                        return False # Fail traversal
                        
        # Continue with normal traversal if didn't slip
        return super().at_traverse(traversing_object, target_location, **kwargs)

