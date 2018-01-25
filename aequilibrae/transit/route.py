class Route:
    def __init__(self):
        self.id = None
        self.agency_id = None
        self.short_name = None
        self.long_name = None
        self.desc = None
        self.type = None
        self.url = None
        self.color = None
        self.text_color = None
        self.sort_order = None
        
        
        self.stops = OrderedDict()