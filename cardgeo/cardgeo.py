class CardGeo:
    bleed: int = 4
    offset: int = 2

    min_w: int = 63
    max_w: int = 63 * 8

    min_h: int = 88
    max_h: int = 88 * 8

    ratio: float = min_h / min_w

    w: int = int(min_w * 4.25)
    h: int = int(min_h * 4.25)

    def __init__(self, geo_data: dict | None = None):
        self.set_data(**geo_data) if geo_data else ...

    def set_data(self, **kwargs):
        [setattr(self, key, val) for key, val in kwargs.items() if isinstance(key, str)]

    def get_data(self) -> dict:
        keys = 'bleed', 'offset', 'min_w', 'min_h', 'max_w', 'max_h', 'w', 'h'
        return {key: getattr(self, key) for key in keys}

    def incr_share(self, factor: float = 0.1):
        val: int = max(1, int(self.w * abs(factor)))
        self.incr_val(val)

    def decr_share(self, factor: float = 0.1):
        val: int = min(-1, -int(self.w * abs(factor)))
        self.decr_val(val)

    def incr_val(self, val: int):
        self.w = min(self.max_w, self.w + abs(val))
        self.h = min(self.max_h, int(self.w * self.ratio))

    def decr_val(self, val: int):
        self.w = max(self.min_w, self.w - abs(val))
        self.h = max(self.min_h, int(self.w * self.ratio))
