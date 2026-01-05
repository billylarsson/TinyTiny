from PIL              import Image
from PIL.ImageDraw    import ImageDraw
from PIL.ImageQt      import ImageQt
from PyQt6            import QtCore, QtGui, QtWidgets
from cardgeo.cardgeo  import CardGeo
from ui.basics        import Label, MoveLabel, ResizeLabel, ShadeLabel
from useful.breakdown import search_cards, tweak_query
from useful.database  import Card, MTGData, Set
from useful.images    import CardImageLocation
from useful.tech      import add_rgb, shrinking_rect, sub
import os, time

class Title(ShadeLabel):
    min_h: int = 26
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.textlabel.setStyleSheet('background:transparent;color:white;font:12px')
        self.textlabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

    def show_title(self):
        if not self.master.card_data:
            name: str = 'COMMANDER'
        else:
            name: str = self.master.card_data[Card.name].upper()

        size: int = 20
        while size > 5 and self.textlabel.get_text_height() > self.height() + 6:
            size -= 1
            self.textlabel.alter_stylesheet('font', f'font:{size}px')

        while len(name) > 5 and self.textlabel.get_text_width(name) + 10 > self.width():
            name = name[:-4] + '...'

        self.textlabel.setText(name)

    def resizeEvent(self, *args):
        w, h = self.width(), self.height()
        [obj.resize(w, h) for obj in (self.textlabel, self.shadelabel,)]
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

        self.show_title()


class ImageLabel(Label):
    img_loc = None
    def show_commander(self):
        self.clear()

        if (not self.master.master.card_data and self.img_loc is not None) or self.img_loc is not None:
            self.img_loc.stop_download()
            self.img_loc = None

        if self.master.master.card_data:
            self.img_loc = CardImageLocation(self.master.master.card_data)
            self.set_image()

    def set_image(self):
        self.clear()
        if os.path.exists(self.img_loc.full_path):
            self.download_finished(True)
        else:
            if self.img_loc.successful_download is None:
                self.img_loc.download_image(finished_fn=self.download_finished)

    def download_finished(self, successful: bool):
        if successful:
            self.smart_croped_image() or self.fallback_image()

    def fallback_image(self) -> bool | None:
        size: tuple = self.width(), self.height(),
        try:
            im = Image.open(self.img_loc.full_path)
            chop_w: int = im.width // 75
            chop_h: int = im.height // 75
            crop_args = chop_w, chop_h, (im.width - 1) - chop_w, (im.height - 1) - chop_h
            im = im.crop(crop_args)
            qim = ImageQt(im)
            pixmap = QtGui.QPixmap.fromImage(qim).scaled(*size, transformMode=QtCore.Qt.TransformationMode(1))
        except:
            ...
        else:
            self.setPixmap(pixmap)
            if not self.hasScaledContents():
                self.setScaledContents(True)
            return True

    def smart_croped_image(self) -> bool | None:
        size: tuple = self.width(), self.height(),
        try:
            large_im = Image.open(self.img_loc.full_path)
            small_im = large_im.resize(size, resample=Image.Resampling.NEAREST)
            datas = small_im.getdata()

            yx: dict[int, int] = {(small_im.height // 6) * n: -1 for n in range(1, 6)}
            w: int = small_im.width
            for y in yx:
                row_ix: int = y * w
                vals: list = [sum(datas[row_ix + x]) for x in range(1, 4)]
                val: int = sum(vals) // len(vals)
                min_val: int = max(0, min(val // 2, val - 30))
                max_val: int = min(int(val * 1.5), 255 * 3)

                for x in range(w // 75, w // 10):
                    ix: int = row_ix + x
                    val: int = sum(datas[ix])
                    if val >= max_val or val <= min_val:
                        yx[y]: int = x - 1
                        break

            vals: list[int] = sorted(v for _, v in yx.items() if v > 0)
            val: int = sum(vals[1:-1]) // len(vals) - 2
            factor: float = large_im.width / small_im.width
            val: int = int(val * factor)
            chop_w: int = val
            chop_h: int = val
            crop_args = chop_w, chop_h, (large_im.width - 1) - chop_w, (large_im.height - 1) - chop_h
            im = large_im.crop(crop_args)
            qim = ImageQt(im)
            pixmap = QtGui.QPixmap.fromImage(qim).scaled(*size, transformMode=QtCore.Qt.TransformationMode(1))
        except:
            ...
        else:
            self.setPixmap(pixmap)
            if not self.hasScaledContents():
                self.setScaledContents(True)
            return True

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

class Commander(ResizeLabel):
    raise_time: float = 0.0  # keeps track on which of all decks that are on top when drag_n_dropping
    min_w: int = CardGeo.min_w
    min_h: int = CardGeo.min_h + Title.min_h
    settings_var: str = 'commander_spotlight'
    card_data: tuple | None = None
    def __init__(self, master, deckbox, **kwargs):
        self.main = master
        self.showbox = deckbox
        self.deckbox = deckbox
        self.deck = deckbox.deck
        super().__init__(master, min_w=self.min_w, min_h=self.min_h, **kwargs)
        self.title = Title(self)
        self.image_background = ImageBackGround(self)
        self.image_background.setStyleSheet('background:black')
        self.image_label = ImageLabel(self.image_background)
        coords: tuple | None = self.get_saved_coords()
        self.setGeometry(*coords) if coords else self.resize(CardGeo.w, Title.min_h + CardGeo.h)

    def closeEvent(self, a0):
        self.deleteLater()

    def show_commander(self):
        cmd_data: dict[str, int] | None = self.deck.get('commander', None)
        if cmd_data:
            scryfall_id: str = next(iter(cmd_data))
            q: str = 'select * from cards where scryfall_id is (?) and (side is "a" or side is null)'
            v: tuple = scryfall_id,
            self.card_data: tuple | None = MTGData.cursor.execute(q, v).fetchone()
        else:
            self.card_data: tuple | None = None

        self.image_label.show_commander()
        self.title.show_title()
        self.deckbox.is_commander = self.card_data is not None

    def resizeEvent(self, a0):
        w, h = self.width(), self.height()
        self.title.resize(w, self.title.min_h)
        args: tuple = 0, self.title.geometry().bottom(), w, h - self.title.height()
        self.image_background.setGeometry(*args)
        args = 2, 2, self.image_background.width() - 4, self.image_background.height() - 4
        self.image_label.setGeometry(*args)
        self.show_commander()

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
        self.raise_time = time.time()
        if self.is_grabbed:
            self.save_coords()

        if ev.button().value != 1:
            for showcase in [x['showcase'] for x in self.deckbox.cards if x['showcase']]:
                if showcase.slot in 'commander' and showcase.card_data == self.card_data:
                    showcase.move_to_slot('maindeck')
                    self.show_commander()
                    break

        super().mouseReleaseEvent(ev)

    def get_saved_coords(self) -> tuple | None:
        try:
            lft, top, rgt, btm = self.deck[self.settings_var]['geo'][:4]
        except (TypeError, KeyError):
            ...
        else:
            w, h = rgt - lft, btm - top
            lft = min(self.main.width() - 50, lft)
            top = min(self.main.height() - 50, top)
            lft, top = max(0, lft), max(0, top)
            return lft, top, w, h

    def save_coords(self):
        geo = self.geometry()
        coords: tuple = geo.left(), geo.top(), geo.right(), geo.bottom()
        if self.settings_var not in self.deck:
            self.deck[self.settings_var]: dict = {}
        self.deck[self.settings_var]['geo']: tuple = coords
        self.showbox.save_deck()


    def insert_card_into_box(self, scryfall_id: str):
        q: str = 'select * from cards where scryfall_id is (?) and (side is "a" or side is null)'
        v: tuple = scryfall_id,
        self.card_data: tuple | None = MTGData.cursor.execute(q, v).fetchone()
        self.deckbox.insert_card_into_box(scryfall_id, slot='commander')
        self.show_commander()
