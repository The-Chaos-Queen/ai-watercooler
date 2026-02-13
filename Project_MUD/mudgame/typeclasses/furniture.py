from typeclasses.objects import Object

class FurnitureObject(Object):
    """
    Objects people can interact with.
    """
    def at_object_creation(self):
        self.db.can_sit = True
        self.db.is_instrument = False

class InstrumentObject(FurnitureObject):
    """
    Musical instruments.
    """
    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_instrument = True
        self.tags.add("instrument")
