from PIL              import Image
from PIL.ImageDraw    import ImageDraw
from PIL.ImageQt      import ImageQt
from PyQt6            import QtCore, QtGui, QtWidgets
from cardgeo.cardgeo  import CardGeo
from ui.basics        import Label, MoveLabel, ShadeLabel
from useful.breakdown import search_cards, tweak_query
from useful.tech      import add, add_rgb, shrinking_rect, sub, sub_rgb


class SearchBar(Label):
    min_h: int = 36
    settings_var: str = 'searchbar...'
    def __init__(self, master, **kwargs):
        self.main = master.main
        self.searchbox = master
        super().__init__(master, **kwargs)
        self.background = Label(self)
        self.lineedit = QtWidgets.QLineEdit(self)
        self.lineedit.setStyleSheet('border:0px;color:rgb(210,210,210);background:transparent;font:16px')
        self.lineedit.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.lineedit.setContentsMargins(5, 0, 5, 0)
        self.lineedit.setText(self.main.load_setting(self.settings_var) or '')
        self.lineedit.returnPressed.connect(self.return_pressed)

    def return_pressed(self):
        text: str = self.lineedit.text().strip()
        self.main.save_setting(self.settings_var, text)
        if not text:
            return

        tweaked_text: str = tweak_query(text)
        queue: list = search_cards(text=tweaked_text)
        if not queue:
            return

        self.searchbox.clear_queue()
        self.searchbox.clear_canvas()
        self.searchbox.add_queue(queue)
        self.searchbox.sort_cards()
        if self.searchbox.queue_size != self.searchbox.batch_size:
            self.searchbox.reset_queue_size()
            return

        self.searchbox.draw_next_card()


    def resizeEvent(self, a0):
        w, h = self.width(), self.height()
        self.background.resize(w, h)
        self.lineedit.resize(w, h)

        margin: int = 12
        size: int = 20
        self.background.setFont(self.lineedit.font())
        self.background.setText('XXX')
        bck_stylesheet: str = self.background.styleSheet()
        tmp_stylesheet: str = self.lineedit.styleSheet()
        self.background.setStyleSheet(tmp_stylesheet)
        self.background.alter_stylesheet(key='font', val=f'{size}px')
        while self.background.get_text_height() + margin > h and size > 7:
            self.background.alter_stylesheet(key='font', val=f'{size}px')
            size -= 1

        new_stylesheet: str = self.background.styleSheet()
        self.lineedit.setStyleSheet(new_stylesheet)
        self.background.setStyleSheet(bck_stylesheet)

        self.draw_background_idle()

    def enterEvent(self, event):
        self.draw_background_hover()

    def leaveEvent(self, a0):
        self.draw_background_idle()

    def draw_background_hover(self):
        args: tuple = 'RGBA', (self.background.width(), self.background.height()), (25,25,25,255)
        im = Image.new(*args)
        draw = ImageDraw(im)

        r, g, b, a = 45, 55, 60, 255
        for n in range(3):
            xy: tuple = shrinking_rect(n, im.width, im.height)
            draw.rectangle(xy=xy, outline=(r, g, b, a))
            r, g, b = add_rgb(r, g, b, min_add=50)

        for n in range(3, 4):
            xy: tuple = shrinking_rect(n, im.width, im.height)
            draw.rectangle(xy=xy, outline=(0, 0, 0, 255))

        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)


    def draw_background_idle(self):
        args: tuple = 'RGBA', (self.background.width(), self.background.height()), (25,25,25,255)
        im = Image.new(*args)
        draw = ImageDraw(im)

        r, g, b, a = 25, 35, 40, 255
        for n in range(3):
            xy: tuple = shrinking_rect(n, im.width, im.height)
            draw.rectangle(xy=xy, outline=(r, g, b, a))
            r, g, b = add_rgb(r, g, b, min_add=50)

        for n in range(3, 4):
            xy: tuple = shrinking_rect(n, im.width, im.height)
            draw.rectangle(xy=xy, outline=(0, 0, 0, 255))

        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)

        r, g, b, a = 25, 35, 40, 255
        for n in range(3):
            xy: tuple = shrinking_rect(n, *im.size)
            draw.rectangle(xy=xy, outline=(r, g, b, a))
            r, g, b = add_rgb(r, g, b, min_add=50)

        for n in range(3, 4):
            xy: tuple = shrinking_rect(n, *im.size)
            draw.rectangle(xy=xy, outline=(0, 0, 0, 255))

        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)

class MoreBTN(Label):
    min_w: int = 80

    def __init__(self, master, **kwargs):
        self.searchbox = master.searchbox
        self.databar = master
        super().__init__(master, **kwargs)
        self.background = Label(self)
        self.textlabel = ShadeLabel(self, x_offset=-2, y_offset=-2)
        self.textlabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.textlabel.setStyleSheet('background:transparent;color:rgb(200,200,200);font:16px;font-weight:500')
        self.textlabel.setText('NEXT')

    def resizeEvent(self, a0):
        w, h = self.width(), self.height()
        self.background.resize(w, h)
        self.textlabel.resize(w, h)
        self.draw_background_idle()

        margin: int = 10
        size: int = 20
        self.textlabel.alter_stylesheet(key='font', val=f'{size}px')
        while self.textlabel.get_text_height() + margin > h and size > 7:
            self.textlabel.alter_stylesheet(key='font', val=f'{size}px')
            size -= 1

    def enterEvent(self, event):
        self.draw_background_hover()

    def leaveEvent(self, a0):
        self.draw_background_idle()

    def draw_background_hover(self):
        is_empty: bool = not any(not box['showcase'] for box in self.master.master.cards)

        args: tuple = 'RGBA', (self.background.width(), self.background.height()), (25, 25, 25, 0)
        im = Image.new(*args)
        draw = ImageDraw(im)

        if not is_empty:
            self.textlabel.setText('NEXT')
            self.textlabel.alter_stylesheet(key='color', val='rgb(255,255,255)')
            r, g, b, a = 40, 40, 40, 255
            n: int = 1
            while n < im.height // 2:
                xy: tuple = shrinking_rect(n, im.width, im.height)
                draw.rectangle(xy=xy, outline=(r, g, b, a))
                r, g, b = add_rgb(r, g, b, factor=0.15, max_val=120)
                n += 1
        else:
            self.textlabel.setText('...')
            self.textlabel.alter_stylesheet(key='color', val='rgb(200,200,200)')
            r, g, b, a = 40, 40, 40, 255
            n: int = 1
            while n < im.height // 2:
                xy: tuple = shrinking_rect(n, im.width, im.height)
                draw.rectangle(xy=xy, outline=(r, g, b, a))
                r, g, b = add_rgb(r, g, b, factor=0.1, max_val=75)
                n += 1

        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)

    def draw_background_idle(self):
        is_empty: bool = not any(not box['showcase'] for box in self.master.master.cards)

        args: tuple = 'RGBA', (self.background.width(), self.background.height()), (25, 25, 25, 0)
        im = Image.new(*args)
        draw = ImageDraw(im)

        if not is_empty:
            self.textlabel.setText('NEXT')
            self.textlabel.alter_stylesheet(key='color', val='rgb(240,240,240)')
            r, g, b, a = 40, 40, 40, 255
            n: int = 1
            while n < im.height // 2:
                xy: tuple = shrinking_rect(n, im.width, im.height)
                draw.rectangle(xy=xy, outline=(r, g, b, a))
                r, g, b = add_rgb(r, g, b, factor=0.15, max_val=100)
                n += 1
        else:
            self.textlabel.setText('...')
            self.textlabel.alter_stylesheet(key='color', val='rgb(150,150,150)')
            r, g, b, a = 40, 40, 40, 255
            n: int = 1
            while n < im.height // 2:
                xy: tuple = shrinking_rect(n, im.width, im.height)
                draw.rectangle(xy=xy, outline=(r, g, b, a))
                r, g, b = add_rgb(r, g, b, factor=0.1, max_val=75)
                n += 1

        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)

    def mouseReleaseEvent(self, ev):
        if self.searchbox.is_drawing():
            self.searchbox.extend_queue_size()
            return

        self.searchbox.draw_next_card()

class QueueStatus(Label):
    min_w: int = 100
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.background = Label(self)
        self.textlabel = ShadeLabel(self)
        self.textlabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.textlabel.setStyleSheet('background:rgb(30,30,30);color:rgb(200,200,200);font:12px')
        self.textlabel.setFont(QtGui.QFont('monospace'))
        self.textlabel.setText('...')

    def resizeEvent(self, a0):
        w, h = self.width(), self.height()
        self.textlabel.resize(w, h)
        self.background.resize(w, h)

        args: tuple = 'RGBA', (w, h), (125, 125, 125, 255)
        im = Image.new(*args)
        draw = ImageDraw(im)

        draw.line(xy=(0, 0, 0, im.height), fill=(50, 50, 50, 255))
        draw.line(xy=(im.width - 1, 0, im.width - 1, im.height), fill=(50, 50, 50, 255))

        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)

    def update_status(self):
        queue: list = self.master.master.cards
        total: int = len(queue)
        if not total:
            self.textlabel.setText('...')
        else:
            shown: int = sum(1 if card['showcase'] else 0 for card in queue)
            self.textlabel.setText(f'SHOWING {shown} / {total}')
            text_w: int = self.textlabel.get_text_width() + 20
            self.resize(max(text_w, self.min_w), self.height())


class ActiveRevBTN(ShadeLabel):
    min_w: int = 100
    active: bool = False
    reversed: bool = False
    font_size: int = 10
    var: str = ''
    bg_col: tuple = 70,70,70
    tx_col: tuple = 200,200,200
    border_col: tuple = 20,20,20
    adjustable_fontsize: bool = True
    def __init__(self, master, var: str = '', adjustable_fontsize: bool = True, **kwargs):
        self.adjustable_fontsize: bool = adjustable_fontsize
        self.var: str = var or self.var
        super().__init__(master, **kwargs)
        self.background = Label(self)
        self.background.lower()
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f'background:transparent;color:{self.tx_col};font:{self.font_size}px')
        self.setText(self.var)

    def resizeEvent(self, *args):
        super().resizeEvent(*args)

        w, h = self.width(), self.height(),
        if w > 6 and h > 6:
            [obj.resize(w, h) for obj in (self.background,)]
            if self.adjustable_fontsize:

                size: int = 30

                wb: int = min(40, max(w // 8, 2))
                hb: int = min(10, max(h // 5, 2))

                wb += 1 if wb % 2 else 0
                hb += 1 if hb % 2 else 0

                while size == 30 or size > 5 and (self.get_text_width() > w - wb or self.get_text_height() > h - hb):
                    self.alter_stylesheet(key='font', val=f'{size}px')
                    size -= 1

            self.draw_background_idle()


    def enterEvent(self, event):
        self.draw_background_hover()

    def leaveEvent(self, a0):
        self.draw_background_idle()

    def draw_background_idle(self):
        if not self.active:
            bg_col: tuple = self.bg_col
        else:
            bg_col: tuple = self.bg_col[:3]
            if all(bg_col[0] == col for col in bg_col[1:]):
                r, g, b = bg_col
                bg_col: tuple = sub(r, factor=0.2), add(g, factor=0.3), sub(b, factor=0.2)
            else:
                bg_col: tuple = add_rgb(*bg_col, factor=0.25)

        self.draw_background(bg_col=bg_col, border_col=self.border_col)
        if not self.active:
            self.alter_stylesheet(key='color', val=f'rgb{self.tx_col}')
        else:
            rgb: tuple = add_rgb(*self.tx_col[:3], factor=0.5)
            self.alter_stylesheet(key='color', val=f'rgb{rgb}')

    def draw_background_hover(self):
        if not self.active:
            bg_col: tuple = add_rgb(*self.bg_col[:3], factor=0.45)
        else:
            bg_col: tuple = self.bg_col[:3]
            if all(bg_col[0] == col for col in bg_col[1:]):
                bg_col: tuple = bg_col[0], add(bg_col[1], factor=0.55), bg_col[2]
            else:
                bg_col: tuple = add_rgb(*bg_col, factor=0.5)

        border_col: tuple = add_rgb(*self.border_col[:3], factor=1.0)
        self.draw_background(bg_col=bg_col, border_col=border_col)

        if not self.active:
            rgb: tuple = add_rgb(*self.tx_col[:3], factor=0.25)
            self.alter_stylesheet(key='color', val=f'rgb{rgb}')
        else:
            rgb: tuple = add_rgb(*self.tx_col[:3], factor=0.5)
            self.alter_stylesheet(key='color', val=f'rgb{rgb}')


    def draw_background(self, bg_col: tuple, border_col: tuple):
        w, h = self.width(), self.height()
        args: tuple = 'RGBA', (w, h), bg_col
        im = Image.new(*args)
        draw = ImageDraw(im)

        org_r, org_g, org_b = bg_col[:3]
        r, g, b = add_rgb(*bg_col[:3], factor=0.5)
        for y in range(im.height // 2):
            draw.line(xy=(0, y, im.width, y), fill=(r, g, b))
            r = max(sub(r, min_sub=2), org_r)
            g = max(sub(g, min_sub=2), org_g)
            b = max(sub(b, min_sub=2), org_b)

        if self.reversed and self.active:
            top: int = im.height // 2
            btm: int = im.height
            lft: int = im.width - top
            rgt: int = im.width
            if lft < rgt:
                r, g, b = add_rgb(*bg_col[:3], factor=0.45)
                g = sub(g, min_sub=50)
                for x in range(lft, rgt):
                    draw.line(xy=(x, btm, x + top, top), fill=(r, g, b))

                draw.line(xy=(lft, btm, rgt, top), fill=(20, 20, 20))

        rgb: tuple = border_col[:3]
        for n in range(1):
            xy: tuple = shrinking_rect(n, *im.size)
            draw.rectangle(xy, outline=rgb)
            rgb = add_rgb(*rgb, min_add=25)


        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)


class SortBTN(ActiveRevBTN):
    def __init__(self, master, var: str, adjustable_fontsize: bool = False, **kwargs):
        master.sort_btns.append(self)
        self.main = master.main
        self.databar = master.databar
        self.searchbox = master.searchbox
        self.var: str = var
        super().__init__(master, adjustable_fontsize=adjustable_fontsize, **kwargs)
        self.setStyleSheet('background:transparent;color:rgb(200,200,200);font:12px')
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

    def mouseReleaseEvent(self, ev):
        self.reversed = ev.button().value == 2
        settings_var: str = self.master.settings_var
        for btn in self.master.sort_btns:
            btn.active = btn == self
            btn.reversed = self.reversed if btn.active else False
            btn.draw_background_hover() if btn.active else btn.draw_background_idle()

        self.main.save_setting(settings_var, (self.var, self.reversed,))
        self.searchbox.sort_cards()

        showcases: list = [obj['showcase'] for obj in self.searchbox.cards if obj['showcase']]
        self.searchbox.reposition_these_showcases(showcases)
        self.searchbox.adjust_move_canvas_height()

class Sorters(Label):
    has_expanded: bool = False
    settings_var: str = 'active_sort'
    def __init__(self, master, **kwargs):
        self.settings_var = master.master.settings_var + self.settings_var
        self.sort_btns: list[SortBTN] = []
        self.main = master.master.main
        self.databar = master
        self.searchbox = master.searchbox
        super().__init__(master, **kwargs)
        self.name = SortBTN(self, var='sort_name')
        self.rarity = SortBTN(self, var='sort_rarity')
        self.cmc = SortBTN(self, var='sort_cmc')
        self.color = SortBTN(self, var='sort_color')
        self.type = SortBTN(self, var='sort_type')
        self.power = SortBTN(self, var='sort_power')
        self.toughness = SortBTN(self, var='sort_toughness')

    def expand_buttons(self, height: int | None = None):
        self.has_expanded: bool = True
        var_name, rev = self.main.load_setting(self.settings_var) or ('name', False)
        h: int = int(height) or self.height()
        x: int = 0
        for btn in self.sort_btns:
            if var_name in btn.var:
                btn.active = True
                btn.reversed = rev

            parts: list[str] = btn.var.split('_')
            text: str = parts[-1].upper()
            btn.setText(text)
            text_w: int = btn.get_text_width() + 20
            btn.setGeometry(x, 0, text_w, h)
            x += text_w

class SizeLabel(ShadeLabel):
    def __init__(self, master, **kwargs):
        self.resizer = master
        self.card_geo: CardGeo = self.resizer.card_geo
        super().__init__(master, **kwargs)
        self.setFont(QtGui.QFont('monospace'))
        self.setStyleSheet('background:transparent;color:rgb(170,170,170);font:12px;font-weight:600')
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter|QtCore.Qt.AlignmentFlag.AlignRight)
        self.setContentsMargins(0,0,10,0)

    def mouseReleaseEvent(self, ev):
        val: int = 1 if ev.button().value == 1 else -1
        self.card_geo.incr_val(val) if val > 0 else self.card_geo.decr_val(val)
        self.resizer.save_geo_data()
        self.resizer.update_textlabel()
        self.resizer.resize_and_resposition_showcases()
        self.resizer.redraw_showcases()

class ResizeSlider(MoveLabel):
    fixed_top: int = -2
    def expand(self):
        slide_w: int = max(15, self.master.height() // 2)
        slide_h: int = max(20, self.master.height() + 4)
        self.resize(slide_w, slide_h)

    def get_min_x(self) -> int:
        return self.master.background.geometry().left() + 5

    def get_max_x(self) -> int:
        return self.master.background.geometry().right() - self.width() - 5

    def position(self):
        cg: CardGeo = self.master.card_geo
        factor: float = cg.min_w / cg.w
        rng: int = self.master.background.width() - self.width()
        lft: int = self.master.background.geometry().left() + int(rng * factor)
        self.move(lft, self.fixed_top)

    def mouseMoveEvent(self, ev):
        if self.is_grabbed is None:
            return

        delta = ev.pos() - self.is_grabbed
        x = (self.pos() + delta).x()
        x = max(self.get_min_x(), x)
        x = min(self.get_max_x(), x)
        self.move(x, self.fixed_top)

        self.master.set_geo_data()
        self.master.update_textlabel()
        self.master.resize_and_resposition_showcases()

    def mouseReleaseEvent(self, ev):
        self.master.save_geo_data()
        self.master.resize_and_resposition_showcases()
        self.master.redraw_showcases()
        super().mouseReleaseEvent(ev)

    def get_wh_from_sliders_pos(self) -> tuple[int, int]:
        cg: CardGeo = self.master.card_geo
        rng: int = self.get_max_x() - self.get_min_x()
        lft: int = max(0, self.geometry().left() - self.get_min_x())
        factor: float = min(1.0, lft / rng)
        factor: float = max(0.0, factor)

        w_rng: int = cg.max_w - cg.min_w
        w: int = cg.min_w + int(w_rng * factor)
        h: int = int(w * cg.ratio)
        return w, h

    def enterEvent(self, event):
        self.draw_background_hover()

    def leaveEvent(self, a0):
        self.draw_background_idle()

    def resizeEvent(self, a0):
        self.draw_background_idle()

    def draw_background_hover(self):
        self.draw_scroller(bg_color=(50, 50, 50, 255), sc_color=(120, 120, 120, 255))

    def draw_background_idle(self):
        self.draw_scroller(bg_color=(0, 0, 0, 255), sc_color=(100, 100, 100, 255))

    def draw_scroller(self, bg_color, sc_color):
        args: tuple = 'RGBA', (self.width(), self.height()), bg_color
        im = Image.new(*args)
        draw = ImageDraw(im)
        w, h = im.width, im.height
        x1, x2, y1, y2 = 0, w - 1, 0, h - 1
        while (x1 != x2) and (y1 != y2):
            x1 += 1 if x1 < x2 else 0
            x2 -= 1 if x2 > x1 else 0
            y1 += 1 if y1 < y2 else 0
            y2 -= 1 if y2 > y1 else 0

            sc_color = tuple(min(255, int(x * 1.1)) for x in sc_color)
            xy = x1, y1, x2, y2
            draw.rectangle(xy=xy, outline=sc_color)

            darker = tuple(255 if x == 255 else int(x * 0.65) for x in sc_color)
            xy = x2, y1, x2, y2
            draw.line(xy=xy, fill=darker)
            xy = x1, y2, x2, y2
            draw.line(xy=xy, fill=darker)

        draw.rectangle(shrinking_rect(0, *im.size), outline=(45,45,45))

        self.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.setPixmap(pixmap)


class CardResizer(Label):
    min_w: int = 240
    settings_var: str = 'resizer'
    def __init__(self, master, geo_data: dict | None = None, **kwargs):
        self.databar = master
        self.showbox = master.master
        self.card_geo = CardGeo(geo_data)
        super().__init__(master, **kwargs)
        self.background = Label(self)
        self.textlabel = SizeLabel(self)
        self.slider = ResizeSlider(self)

    def save_geo_data(self):
        """should be set by child"""

    def redraw_showcases(self):
        for showcase in [obj['showcase'] for obj in self.showbox.cards if obj['showcase']]:
            showcase.draw_background()
            showcase.set_image()

        self.showbox.adjust_move_canvas_height()

    def resize_and_resposition_showcases(self):
        showcases: list = [obj['showcase'] for obj in self.showbox.cards if obj['showcase']]
        if not showcases:
            return

        x, y = self.card_geo.bleed, self.card_geo.bleed
        w, h = self.card_geo.w, self.card_geo.h

        cw: int = self.showbox.move_canvas.width()

        showcases.sort(key=lambda obj: obj.geometry().left())
        showcases.sort(key=lambda obj: obj.geometry().top())

        for showcase in showcases:
            if x + w > cw:
                x = self.card_geo.bleed
                y += h + self.card_geo.offset

            showcase.setGeometry(x, y, w, h)
            x += w + self.card_geo.offset

    def set_geo_data(self):
        w, h = self.slider.get_wh_from_sliders_pos()
        self.card_geo.set_data(w=w, h=h, offset=1 if w < 200 else 2, bleed=3 if w < 200 else 4)

    def update_textlabel(self):
        w, h = self.card_geo.w, self.card_geo.h
        self.textlabel.setText(f'{w} x {h}')

    def resizeEvent(self, a0):
        w, h = self.width(), self.height()
        text_w: int = self.textlabel.get_text_width('640 x 480') + 20
        self.textlabel.resize(text_w, h)
        [label.setGeometry(text_w, 0, w - text_w, h) for label in (self.background,)]

        self.slider.expand()
        self.slider.position()
        self.update_textlabel()

        args: tuple = 'RGBA', (self.background.width(), self.background.height()), (0, 0, 0, 0)
        im = Image.new(*args)
        draw = ImageDraw(im)

        r, g, b, a = 0, 0, 0, 255
        for n in range(3):
            c: int = im.height // 2

            outline: tuple = 90,90,90
            xy: tuple = 10 + n - 1, c + n + 1, im.width - (10 + n - 1), c + n + 1
            draw.line(xy=xy, fill=outline)

            xy: tuple = 10 + n - 1, c - n - 1, im.width - (10 + n - 1), c - n - 1
            draw.line(xy=xy, fill=outline)

            xy: tuple = 10 + n, c - n, im.width - (10 + n), c - n
            draw.line(xy=xy, fill=(r, g, b, a))

            xy: tuple = 10 + n, c + n, im.width - (10 + n), c + n
            draw.line(xy=xy, fill=(r, g, b, a))

            r, g, b = add_rgb(r, g, b, min_add=25)

        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)

        args: tuple = 'RGBA', (w, h), (110, 140, 35, 255)
        im = Image.new(*args)
        draw = ImageDraw(im)
        draw.rectangle(xy=(0,0,text_w, h), fill=(40,40,40))
        draw.rectangle(xy=shrinking_rect(0, *im.size), outline=(0,0,0,255))

        self.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.setPixmap(pixmap)


class DataBar(Label):

    min_h: int = 30
    more_btn = None
    queue_status = None
    card_resizer = None
    import_export = None
    deck_details = None
    sorters = None

    def __init__(self, master, **kwargs):
        self.searchbox = master
        super().__init__(master, **kwargs)
        self.background = Label(self)

    def resizeEvent(self, a0):
        h: int = self.height()
        w: int = self.width()
        self.background.resize(w, h)

        if self.more_btn:
            x: int = 2
            text_w: int = self.more_btn.textlabel.get_text_width() + 40
            self.more_btn.setGeometry(x, 2, min(text_w, self.more_btn.min_w), h - 4)
            x += self.more_btn.width()
        else:
            x: int = 4

        if self.queue_status:
            self.queue_status.setGeometry(x, 4, self.queue_status.min_w, h - 8)
            self.queue_status.update_status()
            x += self.queue_status.width()

        if self.deck_details:
            text_w: int = self.deck_details.get_text_width() + 40
            self.deck_details.setGeometry(x, 4, text_w, h - 8)
            x += self.deck_details.width()

        if self.import_export:
            text_w: int = self.import_export.get_text_width() + 40
            self.import_export.setGeometry(x, 4, text_w, h - 8)
            x += self.import_export.width()

        if self.sorters:
            self.sorters.expand_buttons(height=h - 8)
            sw: int = max(obj.geometry().right() for obj in self.sorters.sort_btns) + 5
            self.sorters.setGeometry(w - sw, 4, sw, h - 8)

        if self.card_resizer:
            if self.sorters:
                rgt: int = self.sorters.geometry().left()
            else:
                rgt: int = self.width()

            min_w: int = self.card_resizer.min_w
            self.card_resizer.setGeometry(rgt - min_w, 4, min_w, h - 8)

        self.draw_background_idle()

    def enterEvent(self, event):
        self.draw_background_hover()

    def leaveEvent(self, a0):
        self.draw_background_idle()

    def draw_background_hover(self):
        args: tuple = 'RGBA', (self.background.width(), self.background.height()), (125, 125, 125, 255)
        im = Image.new(*args)
        draw = ImageDraw(im)

        r, g, b, a = 45, 55, 60, 255
        for n in range(3):
            xy: tuple = shrinking_rect(n, im.width, im.height)
            draw.rectangle(xy=xy, outline=(r, g, b, a))
            r, g, b = add_rgb(r, g, b, min_add=50)

        for n in range(3, 4):
            xy: tuple = shrinking_rect(n, im.width, im.height)
            draw.rectangle(xy=xy, outline=(0, 0, 0, 255))

        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)


    def draw_background_idle(self):
        args: tuple = 'RGBA', (self.background.width(), self.background.height()), (125, 125, 125, 255)
        im = Image.new(*args)
        draw = ImageDraw(im)

        r, g, b, a = 25, 35, 40, 255
        for n in range(3):
            xy: tuple = shrinking_rect(n, im.width, im.height)
            draw.rectangle(xy=xy, outline=(r, g, b, a))
            r, g, b = add_rgb(r, g, b, min_add=50)

        for n in range(3, 4):
            xy: tuple = shrinking_rect(n, im.width, im.height)
            draw.rectangle(xy=xy, outline=(0, 0, 0, 255))

        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)

    def show_queue_status(self):
        self.more_btn.draw_background_idle() if self.more_btn else ...
        self.queue_status.update_status() if self.queue_status else ...
