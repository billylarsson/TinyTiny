from PIL             import Image
from PIL.ImageDraw   import ImageDraw
from PIL.ImageQt     import ImageQt
from PyQt6           import QtCore, QtGui, QtWidgets
from cardgeo.cardgeo import CardGeo
from ui.basics import Label, MoveLabel, ResizeLabel, ShadeLabel, ActiveRevBTN,GroupBTN
from ui.showcase     import CardImage
from useful.database import Card, MTGData, Set,Owned,get_prices,get_regular_price,get_foil_price
from useful.images   import CardImageLocation
from useful.tech     import add, add_rgb, shrinking_rect, sub, sub_rgb
import os
from useful.database import MTGData,card_owned,name_owned

class OwnBTN(GroupBTN):
    font_size: int = 12
    tx_col: tuple = 255, 255, 255

    def __init__(self, main, spotlight, **kwargs):
        self.main = main
        self.spotlight = spotlight
        super().__init__(main, **kwargs)
        self.show()

    def expand(self):
        text: str = self.get_longest_text()
        tw: int = self.get_text_width(text) + 8
        th: int = self.get_text_height(text) + 4
        self.resize(tw, th)

    def card_owned(self) -> bool:
        return self.spotlight.card_data is not None and card_owned(self.spotlight.card_data)

    def name_owned(self) -> bool:
        return self.spotlight.card_data is not None and name_owned(self.spotlight.card_data)

    def show_status(self):
        ...


class AddDelOwned(OwnBTN):
    remove_name: bool = False
    remove_card: bool = False

    def show_status(self):
        own_card: bool = self.card_owned()
        own_name: bool = own_card or self.name_owned()
        for n, mode in enumerate(self.modes):
            if own_name and 'REMOVE' in mode:
                self.mode = n
                self.remove_card = own_card
                self.remove_name = not own_card and own_name
                break
            elif not own_name and 'ADD' in mode:
                self.mode = n
                self.remove_card = False
                self.remove_name = False
                break

        self.active = True
        self.setText(self.modes[self.mode])

        if self.active:
            self.bg_col: tuple = 45, 65, 99, 255
        else:
            self.bg_col: tuple = 95, 65, 49, 255

        self.draw_background_idle()

    def mouseReleaseEvent(self, ev):
        if self.spotlight.card_data is not None:
            card_data = self.spotlight.card_data
            if 'ADD' in self.modes[self.mode]:
                Owned.add_to_textfile(card_data)
            elif self.remove_card:
                Owned.remove_from_textfile(card_data)
            elif self.remove_name:
                cardname: str = card_data[Card.name]
                q: str = 'select * from cards where name is (?)'
                v: tuple = cardname,
                cards: list = MTGData.cursor.execute(q, v).fetchall()
                owned_scry: set[str] = Owned.get_owned()
                diffs: set = {x for x in cards if x[Card.scryfall_id] in owned_scry}
                if diffs:
                    [Owned.remove_from_textfile(x, save=False) for x in diffs]
                    Owned.all_names.remove(cardname) if cardname in Owned.all_names else ...
                    Owned.save_state_to_file()

            self.spotlight.owned_status_btn.show_status()
            self.spotlight.owned_handle_btn.show_status()



class OwnedStatus(OwnBTN):
    def mouseReleaseEvent(self, ev):
        ...

    def show_status(self):
        own_card: bool = self.card_owned()
        own_name: bool = own_card or self.name_owned()
        for n, mode in enumerate(self.modes):
            if own_card and own_name and all(x in mode for x in ['OWN', 'CARD']):
                self.bg_col = 43, 55, 129, 255
                self.mode = n
                break
            elif not own_card and own_name and all(x in mode for x in ['OWN', 'NAME']):
                self.bg_col = 45, 65, 49, 255
                self.mode = n
                break
            elif not own_card and not own_name and all(x in mode for x in ['NOT ', 'OWNED']):
                self.bg_col = 95, 65, 49, 255
                self.mode = n
                break

        self.active = own_card or own_name
        self.setText(self.modes[self.mode])
        self.draw_background_idle()

class SpotLightDataBar(Label):
    min_h: int = 24
    def __init__(self, master, **kwargs):
        self.main = master.main
        super().__init__(master, **kwargs)
        self.background = Label(self)
        self.textlabel = ShadeLabel(self)
        self.textlabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.textlabel.setStyleSheet('background:transparent;color:rgb(200,200,200);font:20px')
        self.textlabel.setText('JUST A LENS')

    def resizeEvent(self, a0):
        w, h = self.width(), self.height()
        [obj.resize(w, h) for obj in (self.background, self.textlabel)]

        size: int = 20
        while size > 5 and self.textlabel.get_text_height() + 8 > self.height():
            self.textlabel.alter_stylesheet('font', f'{size}px')
            size -= 1

        self.draw_background_idle()

    def mouseReleaseEvent(self, ev):
        if ev.button().value != 1:
            self.master.read_only = not self.master.read_only
            self.show_title()

        super().mouseReleaseEvent(ev)

    def show_title(self):
        if self.master.read_only:
            self.textlabel.setText('JUST LOCKED')
        else:
            self.textlabel.setText('JUST A LENS')

    def show_price(self):
        reg, foil = get_prices(self.master.card_data) if self.master.card_data else (0.0, 0.0,)
        if reg or foil:
            if reg >= 100.0 and foil >= 100.0:
                reg, foil = f'{round(reg)}', f'{round(foil)}'
                text: str = f'€{reg} // €{foil}'
            else:
                if reg and not foil:
                    if reg < 100.0:
                        text: str = f'€{reg:.2f}'
                    else:
                        text: str = f'€{round(reg)}'
                elif foil and not reg:
                    if foil < 100.0:
                        text: str = f'€{foil:.2f} (foil)'
                    else:
                        text: str = f'€{round(foil)} (foil)'
                else:
                    reg, foil = f'{reg:.2f}', f'{foil:.2f}'
                    text: str = f'€{reg} // €{foil}'

            self.textlabel.setText(text)
        else:
            self.show_title()

    def enterEvent(self, event):
        self.draw_background_hover()

    def leaveEvent(self, a0):
        self.draw_background_idle()

    def draw_background_hover(self):
        self.textlabel.alter_stylesheet('color', 'rgb(235,235,235)')
        w, h = self.width(), self.height()
        args: tuple = 'RGBA', (w, h), (90, 90, 90, 255)
        im = Image.new(*args)
        draw = ImageDraw(im)

        r, g, b, a = 40, 40, 40, 255
        for n in range(w // 2):
            for x in [n, w - n]:
                draw.line(xy=(x, 0, x, im.height), fill=(r, g, b, a))

            if n % 2:
                r, g, b = add_rgb(r, g, b, min_add=1)
                if r > 90:
                    break

        r, g, b, a = 0, 0, 0, 255
        xy: tuple = shrinking_rect(0, *im.size)
        draw.rectangle(xy=xy, outline=(r, g, b, a))

        r, g, b, a = 175, 175, 175, 255
        for n in range(1, 3):
            xy: tuple = shrinking_rect(n, *im.size)
            draw.rectangle(xy=xy, outline=(r, g, b, a))
            r, g, b = sub(r, factor=0.1), sub(g, factor=0.1), sub(b, factor=0.1)

        r, g, b, a = 0, 0, 0, 255
        xy: tuple = shrinking_rect(3, *im.size)
        draw.rectangle(xy=xy, outline=(r, g, b, a))

        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)

    def draw_background_idle(self):
        self.textlabel.alter_stylesheet('color', 'rgb(210,210,210)')
        w, h = self.width(), self.height()
        bg_col: tuple = 80, 80, 80, 255
        args: tuple = 'RGBA', (w, h), bg_col
        im = Image.new(*args)
        draw = ImageDraw(im)

        r, g, b, a = 30, 30, 30, 255
        for n in range(w // 2):
            for x in [n, w - n]:
                draw.line(xy=(x, 0, x, im.height), fill=(r, g, b, a))

            if n % 2:
                r, g, b = add_rgb(r, g, b, min_add=1)
                if r > 80:
                    break

        r, g, b, a = 0, 0, 0, 255
        xy: tuple = shrinking_rect(0, *im.size)
        draw.rectangle(xy=xy, outline=(r, g, b, a))

        r, g, b, a = 145, 145, 145, 255
        for n in range(1, 3):
            xy: tuple = shrinking_rect(n, *im.size)
            draw.rectangle(xy=xy, outline=(r, g, b, a))
            r, g, b = sub(r, factor=0.1), sub(g, factor=0.1), sub(b, factor=0.1)

        r, g, b, a = 0, 0, 0, 255
        xy: tuple = shrinking_rect(3, *im.size)
        draw.rectangle(xy=xy, outline=(r, g, b, a))


        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)

class ImageBackGround(Label):
    def resizeEvent(self, *args):
        w, h = self.width(), self.height()
        bg_col: tuple = 30, 30, 30, 255
        args: tuple = 'RGBA', (w, h), bg_col
        im = Image.new(*args)
        draw = ImageDraw(im)

        r, g, b, a = 0, 0, 0, 255
        xy: tuple = shrinking_rect(0, *im.size)
        draw.rectangle(xy=xy, outline=(r, g, b, a))

        r, g, b, a = 145, 145, 145, 255
        for n in range(1, 3):
            xy: tuple = shrinking_rect(n, *im.size)
            draw.rectangle(xy=xy, outline=(r, g, b, a))
            r, g, b = sub(r, factor=0.1), sub(g, factor=0.1), sub(b, factor=0.1)

        r, g, b, a = 0, 0, 0, 255
        xy: tuple = shrinking_rect(3, *im.size)
        draw.rectangle(xy=xy, outline=(r, g, b, a))

        self.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.setPixmap(pixmap)

class SpotLightCardImage(CardImage):
    def get_img_loc(self) -> CardImageLocation | None:
        return self.master.master.img_loc

    def mouseReleaseEvent(self, ev):
        if ev.button().value != 1:
            self.master.master.clear_spotlight()
        else:
            card_data: tuple | None = self.master.master.card_data
            double_sided: bool = card_data and card_data[Card.layout] in ['transform', 'modal_dfc', 'meld']
            if double_sided and card_data[Card.side] == 'b':
                q: str = 'select * from cards where side is "a" and scryfall_id is (?)'
                v: tuple = card_data[Card.scryfall_id],
                a_side: tuple | None = MTGData.cursor.execute(q, v).fetchone()
                if a_side and a_side != card_data:
                    self.master.master.borrow_spotlight(a_side)

            super().mouseReleaseEvent(ev)

    def mousePressEvent(self, ev):
        card_data: tuple | None = self.master.master.card_data
        double_sided: bool = card_data and card_data[Card.layout] in ['transform', 'modal_dfc', 'meld']
        if double_sided and card_data[Card.side] == 'a':
            q: str = 'select * from cards where side is "b" and scryfall_id is (?)'
            v: tuple = card_data[Card.scryfall_id],
            b_side: tuple | None = MTGData.cursor.execute(q, v).fetchone()
            if b_side and b_side != card_data:
                self.master.master.borrow_spotlight(b_side)

        super().mousePressEvent(ev)


class SpotLight(ResizeLabel):
    img_loc: None | CardImageLocation = None
    card_data: None | tuple = None
    card_data_backup: None | tuple = None
    read_only: bool = False
    settings_var: str = 'SpotLight!!'

    def __init__(self, main, **kwargs):
        self.main = main
        self.attached_objects: list = []
        super().__init__(main, **kwargs)
        self.owned_handle_btn = AddDelOwned(self.main, spotlight=self, modes=['ADD TO OWNED', 'REMOVE OWNED'])
        self.owned_status_btn = OwnedStatus(self.main, spotlight=self, modes=['CARD OWNED', 'NAME OWNED', 'NOT OWNED'])
        self.attached_objects += [self.owned_status_btn, self.owned_handle_btn]

        self.databar = SpotLightDataBar(self)
        self.image_background = ImageBackGround(self)
        self.image_label = SpotLightCardImage(self.image_background)
        self.image_background.setStyleSheet('background:black')

        geo: tuple = self.get_saved_coords()
        self.setGeometry(*geo)

    def mousePressEvent(self, ev):
        super().mousePressEvent(ev)
        [obj.raise_() for obj in self.attached_objects]

    def closeEvent(self, a0):
        for obj in self.attached_objects:
            try:
                obj.close()
            except RuntimeError:
                ...

    def get_saved_coords(self) -> tuple:
        settings: dict | None = self.main.load_setting(self.settings_var)
        try:
            lft, top, rgt, btm = settings['geo'][:4]
        except (TypeError, KeyError):
            sb = self.main.searchbox
            lft, top = sb.geometry().left(), sb.geometry().bottom(),
            rgt, btm = lft + (CardGeo.w * 2), top + (CardGeo.h * 2),

        w, h = rgt - lft, btm - top
        lft = min(self.main.width() - 50, lft)
        top = min(self.main.height() - 50, top)
        lft, top = max(0, lft), max(0, top)
        return lft, top, w, h

    def save_coords(self):
        settings: dict = self.main.load_setting(self.settings_var) or {}
        geo = self.geometry()
        settings['geo']: tuple = geo.left(), geo.top(), geo.right(), geo.bottom()
        self.main.save_setting(self.settings_var, settings)

    def load_saved_spotlight(self):
        settings: dict = self.main.load_setting(self.settings_var) or {}
        scryfall_id: str | None = settings.get('fixed', None)
        if scryfall_id:
            try:
                q: str = 'select * from cards where scryfall_id is (?) and (side is "a" or side is null)'
                v: tuple = scryfall_id,
                card_data: tuple | None = MTGData.cursor.execute(q, v).fetchone() if scryfall_id else None
                if card_data and os.path.exists(CardImageLocation(card_data).full_path):
                    self.fixed_spotlight(card_data)
            except:
                ...

    def mouseMoveEvent(self, ev):
        if self.is_grabbed and self.is_resizing:
            self.is_custom_resized: bool = True
            y: int = int(ev.pos().y())
            ratio: float = CardGeo.w / CardGeo.h
            height: int = max(y - self.image_background.geometry().top(), self.min_h)
            size = int(height * ratio), height
            self.resize(*size)
        else:
            super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        if self.is_grabbed and self.is_resizing:
            self.set_image()

        super().mouseReleaseEvent(ev)
        self.save_coords()

    def clear_spotlight(self):
        if self.read_only:
            return

        self.card_data = None
        self.card_data_backup = None
        self.restore_spotlight()

    def fixed_spotlight(self, card_data: tuple):
        if self.read_only:
            return

        self.card_data = card_data
        self.card_data_backup = card_data
        self.borrow_spotlight(card_data)

        settings: dict = self.main.load_setting(self.settings_var) or {}
        settings['fixed']: str = card_data[Card.scryfall_id]
        self.main.save_setting(self.settings_var, settings)

    def borrow_spotlight(self, card_data: tuple):
        if self.read_only:
            return

        if self.img_loc:
            self.img_loc.stop_download()
            self.img_loc = None

        self.image_label.clear()
        self.card_data_backup = self.card_data
        self.card_data = card_data
        self.img_loc = CardImageLocation(self.card_data)
        self.set_image()
        self.databar.show_price()

    def restore_spotlight(self):
        if self.read_only:
            return

        if self.img_loc:
            self.img_loc.stop_download()
            self.img_loc = None

        self.image_label.clear()
        self.card_data = self.card_data_backup
        if self.card_data:
            self.img_loc = CardImageLocation(self.card_data)
            self.set_image()

        self.databar.show_title()

    def set_image(self):
        if self.read_only:
            return

        if self.img_loc:
            self.image_label.set_image()

        self.owned_status_btn.show_status()
        self.owned_handle_btn.show_status()

    def moveEvent(self, *args):
        super().moveEvent(*args)
        self.btns_follow()

    def btns_follow(self):
        lft, top = self.geometry().right() - self.owned_status_btn.width(), self.geometry().bottom() + 1
        self.owned_status_btn.move(lft, top)

        lft -= self.owned_handle_btn.width()
        self.owned_handle_btn.move(lft, top)

    def resizeEvent(self, a0):
        w, h = self.width(), self.height()
        self.databar.setGeometry(0, 0, w, self.databar.min_h)
        y: int = self.databar.geometry().bottom()
        self.image_background.setGeometry(0, y, w, h - y)

        w, h = self.image_background.width(), self.image_background.height(),
        geo: tuple = CardGeo.bleed, CardGeo.bleed, w - (CardGeo.bleed * 2), h - (CardGeo.bleed * 2)
        self.image_label.setGeometry(*geo)

        self.owned_status_btn.expand()
        self.owned_handle_btn.expand()
        self.btns_follow()
