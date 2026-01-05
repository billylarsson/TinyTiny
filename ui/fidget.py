from PIL             import Image
from PIL.ImageDraw   import ImageDraw
from PIL.ImageQt     import ImageQt
from PyQt6           import QtCore, QtGui, QtWidgets
from ui.basics       import Label
from useful.database import Card, MTGData, Set
from useful.symbols  import ManaSymbols
from useful.tech     import add, add_rgb, shrinking_rect, sub, sub_rgb

class ManaSymbol(Label):
    dark_pm: QtGui.QPixmap | None = None
    light_pm: QtGui.QPixmap | None = None

    def hover(self):
        self.clear()
        self.setPixmap(self.light_pm) if self.light_pm else ...

    def idle(self):
        self.clear()
        self.setPixmap(self.dark_pm) if self.dark_pm else ...

class ManaBar(Label):
    y_offset: int = 6
    def __init__(self, master, card_data: tuple, **kwargs):
        secondary_keys: tuple = 'split', 'aftermath', 'adventure', 'modal_dfc'
        self.y_offset: int = master.min_h // 3
        self.card_data: tuple = card_data
        self.side_a: tuple | None = card_data if card_data[Card.layout] in secondary_keys else None
        self.side_b: tuple | None = None
        self.fidget = master
        self.symbols: list = []
        super().__init__(master, **kwargs)
        self.show_symbols(self.card_data)

    def show_primary_side(self):
        # if single sided, redraw is skipped
        if self.side_a is not None:
            self.show_symbols(self.side_a or self.card_data)
            self.master.position_textlabel_manabar()

    def show_alternative_side(self):
        # if single sided, redraw is skipped
        if self.side_a is not None:
            # side_b is not fetched until requsted
            if self.side_b is None:
                q: str = 'select * from cards where scryfall_id is (?) and side is "b"'
                v: tuple = self.card_data[Card.scryfall_id],
                self.side_b = MTGData.cursor.execute(q, v).fetchone()

            self.show_symbols(self.side_b or self.side_a or self.card_data)
            self.master.position_textlabel_manabar()

    def show_symbols(self, card_data: tuple):
        [self.symbols.pop(n) for n in range(len(self.symbols) - 1, -1, -1)]
        bleed: int = self.y_offset
        w, h = self.fidget.min_h - bleed, self.fidget.min_h - bleed
        costs: list = (card_data[Card.mana_cost] or '').split('}{')
        costs = [var.strip('{ }') for var in costs]

        for var in [var for var in costs if var]:
            sym = ManaSymbol(self)
            drk_pm_var: str = f'{var} {w}x{h} drk'
            lgt_pm_var: str = f'{var} {w}x{h} lgt'
            sym.dark_pm = ManaSymbols.get_pixmap(drk_pm_var)
            sym.light_pm = ManaSymbols.get_pixmap(lgt_pm_var)
            if not sym.dark_pm:
                im = ManaSymbols.get_im(var)
                if im:
                    qim = ImageQt(im)
                    pixmap = QtGui.QPixmap.fromImage(qim).scaled(w, h, transformMode=QtCore.Qt.TransformationMode(1))
                    ManaSymbols.save_pixmap(lgt_pm_var, pixmap)
                    sym.light_pm = pixmap

                    for y in range(im.height):
                        for x in range(im.width):
                            xy: tuple[int, int] = x, y,
                            pixel: tuple = im.getpixel(xy)
                            if pixel[-1] != 0:
                                im.putpixel(xy, value=(*pixel[:3], 225))

                    qim = ImageQt(im)
                    pixmap = QtGui.QPixmap.fromImage(qim).scaled(w, h, transformMode=QtCore.Qt.TransformationMode(1))
                    ManaSymbols.save_pixmap(drk_pm_var, pixmap)
                    sym.dark_pm = pixmap

            if sym.dark_pm:
                x: int = len(self.symbols) * h
                sym.setGeometry(x, 0, w, h)
                sym.setPixmap(sym.dark_pm)
                self.symbols.append(sym)

        if self.symbols:
            self.resize(w * len(self.symbols), h)
            [sym.show() for sym in self.symbols]
        else:
            self.resize(0, h)

class Fidget(Label):
    min_h: int = 24
    def __init__(self, master, showcase, **kwargs):
        self.main = master.main
        self.showcases: set = {showcase}
        self.card_data: tuple = showcase.card_data
        super().__init__(master, **kwargs)
        self.background = Label(self)
        self.textlabel = Label(self)
        self.amount_label = Label(self)
        self.cardname_label = Label(self)
        self.textlabel.setStyleSheet('background:transparent;color:white;font:12px;font-weight:300')
        self.textlabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.textlabel.setContentsMargins(10, 0, 0, 0)
        self.update_text()
        self.mana_bar = ManaBar(self, self.card_data)
        self.foreground = Label(self)

    def get_slot(self) -> set[str]:
        return {x.slot for x in self.showcases}

    def get_cardnames(self) -> list[str]:
        return [x.strip().upper() for x in self.card_data[Card.name].split('//') if x.strip()]

    def get_min_width(self) -> int:
        texts: set[str] = {self.amount_cardname_str(x) for x in [True, False]}
        tw: int = max(self.textlabel.get_text_width(text) for text in texts)
        mw: int = self.mana_bar.width()
        return tw + 30 + mw

    def position_textlabel_manabar(self):
        w, h = self.width(), self.height()
        offset: int = self.mana_bar.y_offset // 2
        mana_x1: int = w - (self.mana_bar.width() + offset)
        self.mana_bar.move(mana_x1, offset)
        self.textlabel.resize(mana_x1, h)

    def resizeEvent(self, a0):
        w, h = self.width(), self.height()
        [obj.resize(w, h) for obj in (self.background, self.foreground,)]
        bg_col: tuple = 0,0,0,0

        args: tuple = 'RGBA', (w, h), bg_col
        im = Image.new(*args)
        draw = ImageDraw(im)

        r, g, b, a = 120, 120, 120, 255
        for n in range(1):
            xy: tuple = shrinking_rect(n, *im.size)
            draw.rectangle(xy, outline=(r, g, b, a))
            r, g, b = add_rgb(r, g, b, min_add=25)

        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)

        self.position_textlabel_manabar()
        self.draw_background_idle()

    def get_amounts(self) -> int:
        return sum(max(showcase.get_amount(), 0) for showcase in self.showcases)

    def update_text(self, **kwargs):
        self.textlabel.setText(self.amount_cardname_str(**kwargs))

    def amount_cardname_str(self, backside: bool = False) -> str:
        amnt: int = self.get_amounts()
        void: str = ' ' * (4 if amnt < 10 else 2)
        names: list[str] = self.get_cardnames()
        if backside:
            return f'{amnt}{void}{names[-1]}'.upper()
        else:
            return f'{amnt}{void}{names[0]}'.upper()


    def mousePressEvent(self, ev):
        next(iter(self.showcases)).center_into_scrollarea()

    def closeEvent(self, a0):
        for name, fidget in self.master.fidgets.items():
            if fidget == self:
                self.master.fidgets.pop(name)
                break

    def enterEvent(self, event):
        self.draw_background_hover()
        showcase = next(iter(self.showcases))
        showcase.draw_background_hover()
        self.main.spotlight.borrow_spotlight(showcase.card_data)
        self.textlabel.alter_stylesheet('font-weight', '500')
        self.update_text(backside=True)
        self.mana_bar.show_alternative_side()

    def leaveEvent(self, a0):
        self.draw_background_idle()
        showcase = next(iter(self.showcases))
        showcase.draw_background_idle()
        self.main.spotlight.restore_spotlight()
        self.textlabel.alter_stylesheet('font-weight', '300')
        self.update_text(backside=False)
        self.mana_bar.show_primary_side()

    def draw_background_hover(self):
        [sym.hover() for sym in self.mana_bar.symbols]
        w, h = self.width(), self.height()

        if 'commander' in self.get_slot():
            bg_col: tuple = 85, 100, 85, 255
        elif 'Basic Land' in (self.card_data[Card.type] or ''):
            bg_col: tuple = 55, 55, 55, 255
        else:
            bg_col: tuple = 70, 70, 70, 255

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

        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)

        args: tuple = 'RGBA', (w, h), (0,0,0,0)
        im = Image.new(*args)
        draw = ImageDraw(im)

        r, g, b, a = 125, 125, 125, 255
        for n in range(1, 3):
            xy: tuple = shrinking_rect(n, *im.size)
            draw.rectangle(xy=xy, outline=(r, g, b, a))
            r, g, b = sub(r, factor=0.25), sub(g, factor=0.25), sub(b, factor=0.25)
            x1, y1, x2, y2 = xy
            draw.line(xy=(x1, y2, x2, y2), fill=sub_rgb(r, g, b, factor=0.50))
            draw.line(xy=(x2, y1, x2, y2), fill=sub_rgb(r, g, b, factor=0.25))

        r, g, b, a = 20, 20, 20, 255
        for n in [0, 3]:
            xy: tuple = shrinking_rect(n, *im.size)
            draw.rectangle(xy, outline=(r, g, b, a))
            r, g, b = add_rgb(r, g, b, min_add=25)

        self.foreground.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.foreground.setPixmap(pixmap)

    def draw_background_idle(self):
        [sym.idle() for sym in self.mana_bar.symbols]

        w, h = self.width(), self.height()
        if 'commander' in self.get_slot():
            bg_col: tuple = 65, 85, 65, 255
        elif 'Basic Land' in (self.card_data[Card.type] or ''):
            bg_col: tuple = 41, 41, 41, 255
        else:
            bg_col: tuple = 50, 50, 50, 255

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

        self.foreground.clear()
        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)


class SlotBox(dict):
    amount: int = 0
    card: tuple = ()
    slot: str = ''
    type: str = ''
    fidget: None | Fidget = None