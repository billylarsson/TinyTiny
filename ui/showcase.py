from PIL             import Image
from PIL.ImageDraw   import ImageDraw
from PIL.ImageQt     import ImageQt
from PyQt6           import QtCore, QtGui, QtWidgets
from cardgeo.cardgeo import CardGeo
from copy            import deepcopy
from ui.basics       import Label, MoveLabel, ResizeLabel
from ui.dragndrop    import DragNDrop
from useful.database import Card, MTGData, Set
from useful.images   import CardImageLocation
from useful.tech     import add, shrinking_rect, sub


class CardImage(Label):

    def get_img_loc(self) -> CardImageLocation | None:
        return self.master.img_loc

    def download_finished(self, successful: bool):
        if successful:
            self.set_image()

    def set_image(self):
        self.clear()
        img_loc = self.get_img_loc()
        if not img_loc:
            if img_loc.successful_download is None:
                img_loc.download_image(finished_fn=self.download_finished)
            return

        self.smart_croped_image() or self.fallback_image()

    def fallback_image(self) -> bool | None:
        size: tuple = self.width(), self.height(),
        img_loc = self.get_img_loc()
        try:
            im = Image.open(img_loc.full_path)
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
        img_loc = self.get_img_loc()
        try:
            large_im = Image.open(img_loc.full_path)
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

class ShowCase(MoveLabel):
    is_fortified: bool = False
    grabbed_at: tuple[int, int] = 0, 0
    drag_n_drop = None

    def __init__(self, move_canvas, card_data: tuple, bag, **kwargs):
        self.main = move_canvas.main
        self.showbox = move_canvas.showbox
        self.card_data: tuple = card_data
        self.bag = bag
        self.img_loc: CardImageLocation = CardImageLocation(self.card_data)
        super().__init__(move_canvas, **kwargs)
        self.image_label = CardImage(self)
        self.background = Label(self)

    def resizeEvent(self, a0):
        [label.resize(self.width(), self.height()) for label in (self.image_label, self.background,)]

    def set_image(self):
        self.image_label.resize(self.width(), self.height())
        self.image_label.set_image()

    def mousePressEvent(self, ev):
        self.showbox.raise_attached_objects()
        super().mousePressEvent(ev)
        if self.is_grabbed:
            self.grabbed_at = self.geometry().left(), self.geometry().top()
            double_sided: bool = self.card_data[Card.layout] in ['transform', 'modal_dfc', 'meld']
            if double_sided and self.card_data[Card.side] == 'a':
                q: str = 'select * from cards where side is "b" and scryfall_id is (?)'
                v: tuple = self.card_data[Card.scryfall_id],
                other_side: tuple | None = MTGData.cursor.execute(q, v).fetchone()
                if other_side:
                    self.img_loc.stop_download()
                    self.img_loc: CardImageLocation = CardImageLocation(other_side)
                    self.set_image()


    def mouseMoveEvent(self, ev):
        super().mouseMoveEvent(ev)
        if not self.is_grabbed:
            return

        mouse_x, mouse_y = int(ev.globalPosition().x()), int(ev.globalPosition().y())
        mouse_x -= self.main.geometry().left()
        mouse_y -= self.main.geometry().top()
        geo = self.showbox.geometry()
        lft, top, rgt, btm = geo.left(), geo.top(), geo.right(), geo.bottom()
        w, h = self.width(), self.height()
        dragging: bool = mouse_x < lft - (w // 4) or mouse_x > rgt + (w // 4)
        dragging = dragging or mouse_y < top - (h // 4) or mouse_y > btm + (h // 4)
        if not dragging:
            if self.drag_n_drop:
                self.drag_n_drop.hide()
            return

        drag_w, drag_h = CardGeo.w // 2, CardGeo.h // 2
        xy: tuple = mouse_x - (drag_w // 2), mouse_y - (drag_h // 2)
        if not self.drag_n_drop:
            self.drag_n_drop = DragNDrop(self.main, self.showbox, self.card_data)
            self.drag_n_drop.setGeometry(*xy, drag_w, drag_h)
            self.drag_n_drop.show()
            self.drag_n_drop.set_image()
        else:
            self.drag_n_drop.show()
            self.drag_n_drop.move(*xy)


    def closeEvent(self, a0):
        self.img_loc.stop_download()
        if self.drag_n_drop:
            try:
                self.drag_n_drop.close()
            finally:
                self.drag_n_drop = None

    def mouseReleaseEvent(self, ev):
        if self.drag_n_drop and self.grabbed_at:
            self.drag_n_drop.drop_card()
            self.drag_n_drop.close()
            self.drag_n_drop = None
            self.move(*self.grabbed_at)

        double_sided: bool = self.card_data[Card.layout] in ['transform', 'modal_dfc', 'meld']
        if double_sided and self.card_data != self.img_loc.db_input:
            self.img_loc.stop_download()
            self.img_loc: CardImageLocation = CardImageLocation(self.card_data)
            self.set_image()

        super().mouseReleaseEvent(ev)
        if ev.button().value == 1:
            self.main.spotlight.fixed_spotlight(self.card_data)
        elif ev.button().value == 2:
            self.is_fortified = not self.is_fortified
            self.draw_background_hover()
        else:
            cards: list = deepcopy(self.bag.cards)
            if ev.button().value == 16:
                cards.reverse()

            cards += [cards[0], cards[0]]
            for n, card in enumerate(cards):
                if card == self.card_data:
                    self.card_data = cards[n + 1]
                    self.img_loc.stop_download()
                    self.img_loc = CardImageLocation(self.card_data)
                    self.set_image()
                    break

    def center_into_scrollarea(self):
        mc = self.showbox.scroller.move_canvas
        sc = self.showbox.scroller.scope_canvas

        want_y: int = (sc.height() // 2) - (self.height() // 2)
        target_y: int = want_y - self.geometry().top()

        mc.move(mc.geometry().left(), min(0, target_y))

    def draw_background(self):
        self.background.resize(self.width(), self.height())
        self.draw_background_idle()
        if not self.background.hasScaledContents():
            self.background.setScaledContents(True)

    def enterEvent(self, event):
        self.draw_background_hover()
        self.main.spotlight.borrow_spotlight(self.card_data)

    def leaveEvent(self, a0):
        self.draw_background_idle()
        self.main.spotlight.restore_spotlight()

    def draw_background_idle(self):
        args: tuple = 'RGBA', (self.background.width(), self.background.height()), (0, 0, 0, 55)
        im = Image.new(*args)
        draw = ImageDraw(im)

        r, g, b, a = 0, 0, 0, 255
        xy: tuple = shrinking_rect(0, *im.size)
        draw.rectangle(xy=xy, outline=(r, g, b, a))

        if self.is_fortified:
            r, g, b, a = 225, 155, 105, 255
            for n in range(1, 5):
                xy: tuple = shrinking_rect(n, *im.size)
                draw.rectangle(xy=xy, outline=(r, g, b, a))
                r, g, b = sub(r, factor=0.15), sub(g, factor=0.25), sub(b, factor=0.25)
        else:
            r, g, b, a = 175, 175, 175, 255
            for n in range(1, 5):
                xy: tuple = shrinking_rect(n, *im.size)
                draw.rectangle(xy=xy, outline=(r, g, b, a))
                r, g, b = sub(r, factor=0.25), sub(g, factor=0.25), sub(b, factor=0.25)

        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)

    def draw_background_hover(self):
        args: tuple = 'RGBA', (self.background.width(), self.background.height()), (0, 0, 0, 0)
        im = Image.new(*args)
        draw = ImageDraw(im)

        r, g, b, a = 50, 50, 50, 255
        xy: tuple = shrinking_rect(0, *im.size)
        draw.rectangle(xy=xy, outline=(r, g, b, a))

        if self.is_fortified:
            r, g, b, a = 255, 215, 105, 255
            for n in range(1, 5):
                xy: tuple = shrinking_rect(n, *im.size)
                draw.rectangle(xy=xy, outline=(r, g, b, a))
                r, g, b = sub(r, factor=0.15), sub(g, factor=0.25), sub(b, factor=0.25)
        else:
            r, g, b, a = 225, 225, 225, 255
            for n in range(1, 4):
                xy: tuple = shrinking_rect(n, *im.size)
                draw.rectangle(xy=xy, outline=(r, g, b, a))
                r, g, b = sub(r, factor=0.25), sub(g, factor=0.25), sub(b, factor=0.25)

        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)

