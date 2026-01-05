from PIL           import Image
from PIL.ImageDraw import ImageDraw
from PIL.ImageQt   import ImageQt
from PyQt6         import QtCore, QtGui, QtWidgets
from ui.basics     import Label, MoveLabel, ShadeLabel
from ui.fidget     import Fidget
from useful.tech   import add, add_rgb, shrinking_rect, sub, sub_rgb

class DeckSize(Label):
    min_w: int = 70
    color_rgb: tuple = 220,220,220
    def __init__(self, master, **kwargs):
        self.databar = master
        self.color_rgb = add_rgb(*self.databar.title.color_rgb, factor=0.0)
        super().__init__(master, **kwargs)
        self.background = Label(self)
        self.textlabel = ShadeLabel(self)
        self.textlabel.setStyleSheet(f'background:transparent;color:rgb{self.color_rgb};font:20px')
        self.textlabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignRight)
        for label in [self.textlabel.shadelabel, self.textlabel.textlabel]:
            label.setContentsMargins(0,0,10,0)

        self.show_decksize()
        self.resize(self.min_w, self.databar.min_h)

    def resizeEvent(self, a0):
        w, h = self.width(), self.height()
        [obj.resize(w, h) for obj in (self.background, self.textlabel)]

        bg_col: tuple = 0,0,0,0

        args: tuple = 'RGBA', (w, h), bg_col
        im = Image.new(*args)
        draw = ImageDraw(im)

        rgb, a = (90, 90, 150), 255

        for n in range(3, 4):
            draw.line(xy=(n, h - 3, n + 10, 1), fill=(10,20,30,255))

        for n in range(4, 8):
            draw.line(xy=(n, h - 3, n + 10, 1), fill=(*rgb, a))
            rgb = add_rgb(*rgb, min_add=5)

        for n in range(8, w):
            draw.line(xy=(n, h - 3, n + 10, 1), fill=(*rgb, a))
            rgb = sub_rgb(*rgb, min_sub=1, min_val=50)

        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)

    def get_decksize(self) -> int:
        amounts: int = 0
        for _, rolldown in self.master.master.types.items():
            fidgets: list[Fidget] = rolldown.get_sorted_fidgets()
            amounts += sum(fidget.get_amounts() for fidget in fidgets) if fidgets else 0

        return amounts

    def show_decksize(self):
        amounts: int = self.get_decksize()
        self.textlabel.setText(str(amounts))


class Title(Label):
    min_w: int = 100
    color_rgb: tuple = 255, 255, 255
    def __init__(self, master, **kwargs):
        self.databar = master
        super().__init__(master, **kwargs)
        self.textlabel = ShadeLabel(self)
        self.textlabel.setStyleSheet(f'background:transparent;color:rgb{self.color_rgb};font:20px;font-weight:600')

        for label in [self.textlabel.textlabel, self.textlabel.shadelabel]:
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
            label.setContentsMargins(10, 0, 0, 0)

        self.textlabel.setText('DECKSIZE')
        self.resize(self.min_w, self.databar.min_h)


    def resizeEvent(self, a0):
        w, h = self.width(), self.height()
        [obj.resize(w, h) for obj in (self.textlabel,)]
        size: int = 20
        while self.textlabel.get_text_height() + 8 > h:
            size -= 1
            self.textlabel.alter_stylesheet('font', f'{size}px')

        for string in self.textlabel.styleSheet().split(';'):
            part1: str = string[:string.find(':')]
            part2: str = string[string.find(':') + 1:]
            if part1.startswith('font') and 'px' in part2:
                self.databar.amounts.textlabel.alter_stylesheet('font', part2)
                break


class DeckStatus(Label):
    min_h: int = 30
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.background = Label(self)
        self.title = Title(self)
        self.amounts = DeckSize(self)

    def show_decksize(self):
        self.amounts.show_decksize()

    def update_status(self):
        self.show_decksize()
        tw: int = max(self.title.textlabel.get_text_width() + 30, self.title.width())
        aw: int = max(self.amounts.textlabel.get_text_width() + 30, self.amounts.width())
        self.title.resize(tw, self.min_h)
        self.amounts.move(tw, 0)
        self.resize(tw + aw, self.min_h)

    def resizeEvent(self, a0):
        w, h = self.width(), self.height()
        [obj.resize(w, h) for obj in (self.background,)]
        self.draw_background_idle()

    def enterEvent(self, event):
        self.draw_background_hover()

    def leaveEvent(self, a0):
        self.draw_background_idle()

    def draw_background_hover(self):
        wall: int = self.amounts.geometry().left()
        w, h = self.width(), self.height()
        bg_col: tuple = 40, 85, 111, 255

        args: tuple = 'RGBA', (w, h), bg_col
        im = Image.new(*args)
        draw = ImageDraw(im)

        org_r, org_g, org_b = bg_col[:-1]
        r, g, b = add_rgb(*bg_col[:-1], factor=0.5)
        for y in range(im.height // 2):
            draw.line(xy=(0, y, wall + 10, y), fill=(r, g, b))
            r = max(sub(r, min_sub=2), org_r)
            g = max(sub(g, min_sub=2), org_g)
            b = max(sub(b, min_sub=2), org_b)

        r, g, b, a = 10, 20, 30, 255
        for n in range(3):
            xy: tuple = shrinking_rect(n, *im.size)
            draw.rectangle(xy, outline=(r, g, b, a))
            r, g, b = add_rgb(r, g, b, min_add=25)

        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)

    def draw_background_idle(self):
        w, h = self.width(), self.height()
        bg_col: tuple = 30, 70, 90, 255

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

        r, g, b, a = 10, 20, 30, 255
        for n in range(3):
            xy: tuple = shrinking_rect(n, *im.size)
            draw.rectangle(xy, outline=(r, g, b, a))
            r, g, b = add_rgb(r, g, b, min_add=25)

        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)

