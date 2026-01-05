from useful.preloads import preloads

hack_strings: list[str] = []
# hack_strings: list[str] = ['update_database', 'import_owned', 'zip_source', 'update_legals', 'import_prices']
hack_string: str = ' '.join(hack_strings)
preloads(hack_string)

from PyQt6             import QtCore, QtGui, QtWidgets
from cardgeo.cardgeo   import CardGeo
from copy              import deepcopy
from ui.deckboxes      import DeckBoxes
from ui.searchbox      import SearchBox
from ui.spotlight      import SpotLight
from useful.threadpool import custom_thread
from useful.update_database import user_datas
import pickle, sys, sqlite3


class Settings(dict):
    storage: dict = {}
    connection = sqlite3.connect(user_datas)
    cursor = connection.cursor()
    try:
        q: str = 'select data from settings where id is 1'
        data: tuple | None = cursor.execute(q).fetchone()
        storage: dict = pickle.loads(data[0])
    except TypeError:
        ...
    except sqlite3.OperationalError:
        with connection:
            q: str = 'CREATE TABLE if not exists settings (id INTEGER PRIMARY KEY AUTOINCREMENT, data BLOB)'
            cursor.execute(q)
            q: str = 'insert into settings values(?,?)'
            v: tuple = None, None,
            cursor.execute(q, v)

    def load_setting(self, key):
        return self.storage.get(key, None)

    def save_setting(self, key, value) -> None:
        self.storage[key] = deepcopy(value)
        with self.connection:
            q: str = 'update settings set data = (?) where id is 1'
            v: tuple = pickle.dumps(self.storage),
            self.cursor.execute(q, v)

class TinyBuilder(QtWidgets.QMainWindow):

    def __init__(self, geo: tuple[int, int, int, int], maximized: bool = True):
        self.settings_handler = Settings()

        super().__init__()
        self.setStyleSheet('background:rgb(25,25,25)')
        self.setStyleSheet('background:rgb(0,0,0)')
        self.setGeometry(*geo)

        self.deckboxes = DeckBoxes(self)
        self.deckboxes.move(2, 2)

        self.searchbox = SearchBox(self)
        self.searchbox.searchbar.lineedit.setFocus()

        self.spotlight = SpotLight(self, min_w=CardGeo.w, min_h=CardGeo.h + 30)

        self.showMaximized() if maximized else self.show()

        self.spotlight.load_saved_spotlight()
        custom_thread(fn=lambda: self.searchbox.searchbar.return_pressed(), delay=0.2)

        uuid: float | None = self.load_setting('recent_deck')
        for deckbox in self.deckboxes.deckboxes:
            if uuid == deckbox.deckbox.get('uuid', -1.0):
                custom_thread(fn=lambda: deckbox.open_btn.open_deck(), delay=0.3)
                break


    def load_setting(self, key):
        return self.settings_handler.load_setting(key)

    def save_setting(self, key, value):
        self.settings_handler.save_setting(key, value)



if '__main__' in __name__:
    app = QtWidgets.QApplication(sys.argv)
    for screen in app.screens():
        if screen == QtGui.QGuiApplication.primaryScreen():
            x: int = screen.geometry().left()
            y: int = screen.geometry().top()
            w: int = screen.geometry().width()
            h: int = screen.geometry().height()

            bleed: int = min(w // 10, h // 10)
            geometry: tuple[int, int, int, int] = bleed, bleed, w - (bleed * 2), h - (bleed * 2),
            break
    else:
        geometry: tuple[int, int, int, int] = 100, 100, 1000, 1000,

    program = TinyBuilder(geometry)
    app.exec()
