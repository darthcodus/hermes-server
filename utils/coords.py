class Coords(object):
    def __init__(self, lat, long):
        self.lat = lat
        self.long = long

    def __hash__(self):
        return hash((self.lat, self.long))
