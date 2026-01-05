from ui.showbox import ShowBox
from ui.databar import SearchBar,DataBar,MoreBTN,QueueStatus,CardResizer,Sorters

class SearchCardResizer(CardResizer):
    def __init__(self, master, **kwargs):
        self.main = master.master.main
        geo_data: dict | None = self.main.load_setting(self.settings_var)
        super().__init__(master, geo_data=geo_data, **kwargs)

    def save_geo_data(self):
        data: dict = self.card_geo.get_data()
        self.main.save_setting(self.settings_var, data)

class SearchBoxDataBar(DataBar):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.sorters = Sorters(self)
        self.queue_status = QueueStatus(self)
        self.card_resizer = SearchCardResizer(self)

class SearchBox(ShowBox):
    settings_var: str = 'SearchBox!'

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.searchbar = SearchBar(self)
        self.databar = SearchBoxDataBar(self)
        self.databar.more_btn = MoreBTN(self.databar)
