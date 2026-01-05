from PIL               import Image
from PIL.ImageDraw     import ImageDraw
from PIL.ImageQt       import ImageQt
from PyQt6             import QtCore, QtGui, QtWidgets
from ui.basics         import Label, ShadeLabel
from ui.deck           import Deck, empty_deck
from useful.tech       import add, add_rgb, add_rgba, alter_stylesheet
from useful.tech       import shrinking_rect, sub, sub_rgb, sub_rgba
from useful.threadpool import custom_thread
import json, time

class DeckButton(Label):
    background_rgba: tuple = 100, 80, 220, 255
    def __init__(self, master, **kwargs):
        self.main = master.main
        self.deck: None | Deck = None
        super().__init__(master, **kwargs)
        self.hover_tip = ShadeLabel(self.master.canvas)
        self.hover_tip.setStyleSheet('background:transparent;color:white;font:20px;font-weight:600')
        self.hover_tip.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.hover_tip.hide()

    def resizeEvent(self, a0):
        self.draw_canvas_off()

    def draw_canvas_off(self):
        im = Image.new(mode='RGBA', size=(self.width(), self.height()), color=(130, 130, 130, 255))
        draw = ImageDraw(im)

        r, g, b, a = 15, 15, 15, 225
        for n in range(1):
            xy: tuple = shrinking_rect(n, *im.size)
            draw.rectangle(xy=xy, outline=(r, g, b, a))
            r, g, b = sub(r, factor=0.25), sub(g, factor=0.25), sub(b, factor=0.25)

        self.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.setPixmap(pixmap)


    def enterEvent(self, event):
        self.draw_canvas_on()
        self.show_hover_text()

    def show_hover_text(self):
        ...

    def draw_canvas_on(self):
        im = Image.new(mode='RGBA', size=(self.width(), self.height()), color=self.background_rgba)
        draw = ImageDraw(im)

        r, g, b, a = self.background_rgba
        for n in range(im.height, -1, -1):
            draw.line(xy=(0, n, im.width, n), fill=(r, g, b, a))
            r, g, b = add(r, min_add=3), add(g, min_add=3), add(b, min_add=3)

        r, g, b, a = 25, 25, 25, 255
        for n in range(1):
            xy: tuple = shrinking_rect(n, *im.size)
            draw.rectangle(xy=xy, outline=(r, g, b, a))
            r, g, b = sub(r, factor=0.25), sub(g, factor=0.25), sub(b, factor=0.25)

        self.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.setPixmap(pixmap)

    def leaveEvent(self, a0):
        self.draw_canvas_off()
        self.master.canvas.lower()
        self.hover_tip.hide()

class DelBTN(DeckButton):
    org_background_rgba: tuple = 100, 80, 20, 255
    background_rgba: tuple = org_background_rgba
    running: bool = False

    def start_countdown(self):
        if self.running:
            return

        self.running = True
        self.hover_tip.setText('DELETING')
        custom_thread(fn=lambda: self.countdown_runner(35), delay=0.1)

    def stop_countdown(self):
        self.running = False
        self.hover_tip.setText('DELETE')
        self.background_rgba = self.org_background_rgba
        self.draw_canvas_on()

    def countdown_runner(self, val: int):
        if not self.running:
            self.stop_countdown()
        else:
            if val > 0:
                r, g, b, a = self.background_rgba
                self.background_rgba = add(r, min_add=10), add(g, min_add=2, max_val=220), add(b, min_add=1, max_val=150), 255
                self.draw_canvas_on()
                if val in [5, 10, 15, 20, 25, 30]:
                    self.hover_tip.setText(self.hover_tip.text() + ' .')
                custom_thread(fn=lambda: self.countdown_runner(val - 1), delay=0.08)
            else:
                uuid: float = self.master.deckbox['uuid']
                self.master.open_btn.close_deck()
                self.main.load_setting('deckboxes') or {}
                deckboxes: dict = self.main.load_setting('deckboxes') or {}
                if uuid in deckboxes:
                    deckboxes.pop(uuid)
                    self.main.save_setting('deckboxes', deckboxes)

                self.master.master.deckboxes.remove(self.master)
                self.master.master.redraw_deckboxes()
                self.master.close()


    def mousePressEvent(self, ev):
        self.start_countdown()

    def mouseReleaseEvent(self, ev):
        self.master.open_btn.close_deck()
        self.master.open_btn.hover_tip.hide()
        self.stop_countdown()

    def enterEvent(self, event):
        super().enterEvent(event)
        canvas = self.master.canvas
        canvas.raise_()
        # self.hover_tip.setGeometry(1, 1, canvas.width() - 2, canvas.height() - 2)
        self.hover_tip.resize(canvas.width(), canvas.height())
        self.hover_tip.raise_()
        self.hover_tip.show()

        self.hover_tip.setText('DELETE')
        size: int = 20
        while self.hover_tip.get_text_height() + 8 > canvas.height() and size > 5:
            size -= 1
            self.hover_tip.alter_stylesheet('font', f'{size}px')


class OpenBTN(DeckButton):
    background_rgba: tuple = 30, 80, 20, 255
    def mouseReleaseEvent(self, ev):
        if ev.button().value == 1:
            if self.deck:
                self.close_deck()
                return

            self.open_deck()
            self.show_hover_text()

    def close_deck(self):
        if self.deck:
            try:
                self.deck.close()
            except RuntimeError:
                ...
            else:
                self.deck.deleteLater()
                self.deck = None
                self.show_hover_text()

    def open_deck(self):
        uuid: float = self.master.deckbox['uuid']
        self.deck = Deck(self.main, uuid)
        self.deck.show()
        self.deck.redraw_deck()
        self.main.save_setting('recent_deck', uuid)

    def show_hover_text(self):
        canvas = self.master.canvas
        canvas.raise_()
        self.hover_tip.setGeometry(1, 1, canvas.width() - 2, canvas.height() - 2)
        self.hover_tip.raise_()
        self.hover_tip.show()

        self.hover_tip.setText('OPEN' if self.deck is None else 'CLOSE')
        size: int = 20
        while self.hover_tip.get_text_height() + 8 > canvas.height() and size > 5:
            size -= 1
            self.hover_tip.alter_stylesheet('font', f'{size}px')


class DeckBox(Label):
    button_w: int = 15
    chars: int = 20
    def __init__(self, master, deckbox: dict, **kwargs):
        self.main = master.main
        self.deckbox: dict = deckbox
        super().__init__(master, **kwargs)
        self.canvas = Label(self)

        style_string: str = (f'background:transparent;'
                             f'color:rgb(0,0,0);'
                             f'font:12px;'
                             f'border:0px;'
                             f'selection-background-color:transparent;'
                             f'selection-color:black;'
                             f'padding:3px')

        self._lineedit = QtWidgets.QLineEdit(self)
        self._lineedit.setText(deckbox['name'])
        self._lineedit.setStyleSheet(style_string)
        self._lineedit.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
        self._lineedit.setContentsMargins(3, 2, 0, 0)

        self.lineedit = QtWidgets.QLineEdit(self)
        self.lineedit.setText(deckbox['name'])
        self.lineedit.setStyleSheet('background:transparent;color:rgb(255,255,255);font:12px;border:0px;padding:3px')
        self.lineedit.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.lineedit.setContentsMargins(5, 0, 0, 0)
        self.lineedit.textChanged.connect(self.text_changed)

        self.open_btn = OpenBTN(self)
        self.del_btn = DelBTN(self)
        font = self.lineedit.font()
        rect = QtGui.QFontMetrics(font).boundingRect('X' * self.chars)
        w, h = rect.width() + 10, self.master.height()
        btns: list = [self.open_btn, self.del_btn]
        self.resize(w + len(btns) * self.button_w, h)

    def text_changed(self, *args):
        text: str = self.lineedit.text().strip()
        self.deckbox['name']: str = text
        uuid: str = self.deckbox['uuid']
        deckboxes: dict = self.main.load_setting('deckboxes') or {}
        deckboxes[uuid]: dict = self.deckbox
        self.main.save_setting('deckboxes', deckboxes)

        self._lineedit.setText(text)

    def resizeEvent(self, a0):
        w, h = self.width(), self.height()
        if w < self.button_w * 3:
            return

        self.open_btn.setGeometry(0, 0, self.button_w, h)
        self.del_btn.setGeometry(w - self.button_w, 0, self.button_w, h)

        lft: int = self.open_btn.geometry().right() + 1
        rgt: int = self.del_btn.geometry().left()
        rest: int = rgt - lft

        for obj in [self.canvas, self._lineedit, self.lineedit]:
            obj.setGeometry(lft, 0, rest, h)

        self.draw_canvas_off()

    def draw_canvas_off(self):
        w, h = self.lineedit.width(), self.lineedit.height()
        bg_col: tuple = 80, 80, 80, 255

        args: tuple = 'RGBA', (w, h), bg_col
        im = Image.new(*args)
        draw = ImageDraw(im)

        org_r, org_g, org_b = bg_col[:-1]
        r, g, b = add_rgb(*bg_col[:-1], factor=0.5)
        for y in range(im.height // 2):
            draw.line(xy=(0, y, im.width - 1, y), fill=(r, g, b))
            r = max(sub(r, min_sub=2), org_r)
            g = max(sub(g, min_sub=2), org_g)
            b = max(sub(b, min_sub=2), org_b)

        r,g,b,a = 20,20,20,255
        for n in range(1):
            xy: tuple = shrinking_rect(n, *im.size)
            draw.rectangle(xy, outline=(r, g, b, a))
            r, g, b = add_rgb(r, g, b, min_add=25)

        self.canvas.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.canvas.setPixmap(pixmap)


    def draw_canvas_on(self):
        w, h = self.lineedit.width(), self.lineedit.height()

        bg_col: tuple = 95, 95, 95, 255

        args: tuple = 'RGBA', (w, h), bg_col
        im = Image.new(*args)
        draw = ImageDraw(im)

        org_r, org_g, org_b = bg_col[:-1]
        r, g, b = add_rgb(*bg_col[:-1], factor=0.5)
        for y in range(im.height // 2):
            draw.line(xy=(0, y, im.width - 1, y), fill=(r, g, b))
            r = max(sub(r, min_sub=2), org_r)
            g = max(sub(g, min_sub=2), org_g)
            b = max(sub(b, min_sub=2), org_b)

        r,g,b,a = 20,20,20,255
        for n in range(1):
            xy: tuple = shrinking_rect(n, *im.size)
            draw.rectangle(xy, outline=(r, g, b, a))
            r, g, b = add_rgb(r, g, b, min_add=25)


        self.canvas.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.canvas.setPixmap(pixmap)

    def enterEvent(self, event):
        self.draw_canvas_on()

    def leaveEvent(self, a0):
        self.draw_canvas_off()

class DeckBoxesMenu(Label):
    def __init__(self, master, **kwargs):
        self.main = master.main
        super().__init__(master, **kwargs)
        self.canvas = Label(self)
        self.textlabel = Label(self)
        self.textlabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.textlabel.setStyleSheet('background:transparent;color:white;font:14px')
        self.textlabel.setText('...')

    def mouseReleaseEvent(self, ev):
        new_deck: dict = empty_deck()
        uuid: float = new_deck['uuid']
        deckboxes: dict = self.main.load_setting('deckboxes') or {}
        deckboxes[uuid]: dict = new_deck
        self.main.save_setting('deckboxes', deckboxes)
        self.master.redraw_deckboxes()
        [x.show() for x in self.master.deckboxes]

    def resizeEvent(self, a0):
        [label.resize(self.width(), self.height()) for label in (self.canvas, self.textlabel)]
        self.draw_canvas_off()

    def enterEvent(self, event):
        self.draw_canvas_on()

    def draw_canvas_off(self):
        im = Image.new(mode='RGBA', size=(self.width(), self.height()), color=(0, 0, 0, 255))
        draw = ImageDraw(im)

        r, g, b, a = 125, 125, 125, 225
        for n in range(3):
            xy: tuple = shrinking_rect(n, *im.size)
            draw.rectangle(xy=xy, outline=(r, g, b, a))
            r, g, b = sub(r, factor=0.25), sub(g, factor=0.25), sub(b, factor=0.25)

        self.canvas.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.canvas.setPixmap(pixmap)


    def draw_canvas_on(self):
        border_rgba: tuple = 100, 80, 220, 255
        im = Image.new(mode='RGBA', size=(self.width(), self.height()), color=(10, 10, 10, 255))
        draw = ImageDraw(im)

        r, g, b, a = border_rgba
        for n in range(im.height, im.height // 4, -1):
            xy: tuple = shrinking_rect(n, *im.size)
            draw.line(xy=xy, fill=(r, g, b, a))
            r, g, b = sub(r, factor=0.1, max_sub=5), sub(g, factor=0.1, max_sub=5), sub(b, factor=0.1, max_sub=5)

        for n in range(1):
            xy: tuple = shrinking_rect(n, *im.size)
            draw.rectangle(xy=xy, outline=(175, 175, 175, 255))

        r, g, b, a = border_rgba
        for n in range(1, 3):
            xy: tuple = shrinking_rect(n, *im.size)
            draw.rectangle(xy=xy, outline=(r, g, b, a))
            r, g, b = sub(r, factor=0.25), sub(g, factor=0.25), sub(b, factor=0.25)


        self.canvas.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.canvas.setPixmap(pixmap)

    def leaveEvent(self, a0):
        self.draw_canvas_off()


class DeckBoxes(Label):
    def __init__(self, main, **kwargs):
        self.main = main
        self.deckboxes: list[DeckBox] = []
        super().__init__(main, **kwargs)
        rect = QtGui.QFontMetrics(QtGui.QFont(self.font())).boundingRect('#')
        h: int = rect.height() + 8
        self.resize(h, h)
        self.menu = DeckBoxesMenu(self)
        self.menu.resize(h, h)
        self.redraw_deckboxes()

    def redraw_deckboxes(self):
        h: int = self.height()
        rgt: int = self.menu.geometry().right() + 2
        for deckbox in self.deckboxes:
            deckbox.move(rgt, 0)
            rgt += deckbox.width() + 4

        for unique, box in (self.main.load_setting('deckboxes') or {}).items():
            if box['uuid'] in {x.deckbox['uuid'] for x in self.deckboxes}:
                continue

            deckbox = DeckBox(self, deckbox=box)
            deckbox.move(rgt, 0)
            rgt += deckbox.width() + 4
            self.deckboxes.append(deckbox)

        self.resize(rgt, h)
