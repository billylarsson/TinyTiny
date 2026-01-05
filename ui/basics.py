from PIL           import Image
from PIL.ImageDraw import ImageDraw
from PIL.ImageQt   import ImageQt
from PyQt6         import QtCore, QtGui, QtWidgets
from useful.tech import add_rgb, shrinking_rect, add, sub


class Label(QtWidgets.QLabel):
    def __init__(self, master, **kwargs):
        self.master = master
        super().__init__(master, **kwargs)
        self.setStyleSheet('background:transparent;color:transparent')

    def alter_stylesheet(self, key: str, val: str):
        parts: list[str] = self.styleSheet().split(';')
        for n, string in enumerate(parts):
            if ':' in string:
                part: str = string[:string.find(':')]
                if part.startswith(key):
                    parts[n]: str = f'{key}:{val}'
                    break
        else:
            parts.append(f'{key}:{val}')

        stylesheet: str = ';'.join(parts)
        if stylesheet != self.styleSheet():
            self.setStyleSheet(stylesheet)

    def get_text_width(self, text: str = '') -> int:
        font, text = self.font(), (text or self.text())
        return QtGui.QFontMetrics(font).boundingRect(text).width()

    def get_text_height(self, text: str = '') -> int:
        font, text = self.font(), (text or self.text())
        return QtGui.QFontMetrics(font).boundingRect(text).height()

class ShadeLabel(Label):
    x_offset: int = -1
    y_offset: int = -1
    def __init__(self, master, x_offset: int = -1, y_offset: int = -1, **kwargs):
        self.x_offset: int = x_offset
        self.y_offset: int = y_offset
        super().__init__(master, **kwargs)
        self.shadelabel = Label(self)
        self.textlabel = Label(self)

    def all_labels_present(self) -> bool:
        return all(var in dir(self) for var in ['shadelabel', 'textlabel'])

    def resizeEvent(self, *args):
        if self.all_labels_present():
            w, h = self.width(), self.height()
            self.shadelabel.setGeometry(self.x_offset, self.y_offset, w, h)
            self.textlabel.resize(w, h)
        else:
            super().resizeEvent(*args)

    def setFont(self, *args, **kwargs):
        if self.all_labels_present():
            self.shadelabel.setFont(*args, **kwargs)
            self.textlabel.setFont(*args, **kwargs)
        else:
            super().resizeEvent(*args, **kwargs)

    def styleSheet(self):
        if self.all_labels_present():
            return self.textlabel.styleSheet()
        else:
            return super().styleSheet()

    def setAlignment(self, flags):
        if self.all_labels_present():
            self.shadelabel.setAlignment(flags)
            self.textlabel.setAlignment(flags)
        else:
            super().setAlignment(flags)

    def setStyleSheet(self, stylesheet: str):
        if self.all_labels_present():
            self.shadelabel.setStyleSheet(stylesheet)
            self.shadelabel.alter_stylesheet(key='color', val='black')
            self.textlabel.setStyleSheet(stylesheet)
        else:
            super().setStyleSheet(stylesheet)

    def setContentsMargins(self, *args, **kwargs):
        if self.all_labels_present():
            self.shadelabel.setContentsMargins(*args, **kwargs)
            self.textlabel.setContentsMargins(*args, **kwargs)
        else:
            super().setContentsMargins(*args, **kwargs)

    def text(self):
        if self.all_labels_present():
            return self.textlabel.text()
        else:
            return super().text()

    def font(self):
        if self.all_labels_present():
            return self.textlabel.font()
        else:
            return super().font()

    def setText(self, text: str):
        if self.all_labels_present():
            self.shadelabel.setText(text)
            self.textlabel.setText(text)
        else:
            super().setText(text)



class MoveLabel(Label):
    def __init__(self, master, **kwargs):
        self.is_grabbed = None
        super().__init__(master, **kwargs)
        self.setMouseTracking(True)

    def mousePressEvent(self, ev):
        if ev.button().value == 1:
            self.is_grabbed = ev.pos()
            self.raise_()
        else:
            self.is_grabbed = None

    def mouseReleaseEvent(self, ev):
        self.is_grabbed = None

    def mouseMoveEvent(self, ev):
        if self.is_grabbed is None:
            return

        delta = ev.pos() - self.is_grabbed
        self.move(self.pos() + delta)

class ResizeLabel(MoveLabel):
    def __init__(self, master, min_w: int = 100, min_h: int = 100, **kwargs):
        self.min_w: int = min_w
        self.min_h: int = min_h
        self.is_resizing = False
        self.is_custom_resized: bool = False
        super().__init__(master, **kwargs)

    def mousePressEvent(self, ev):
        super().mousePressEvent(ev)
        if ev.button().value == 1:
            bleed_w: int = max(20, self.width() // 20)
            bleed_h: int = max(20, self.height() // 20)
            x_near_edge: bool = ev.pos().x() > self.width() - bleed_w
            y_near_edge: bool = ev.pos().y() > self.height() - bleed_h
            self.is_resizing: bool = x_near_edge and y_near_edge
            self.raise_()
        else:
            self.is_grabbed = None

    def mouseMoveEvent(self, ev):
        if self.is_grabbed and self.is_resizing:
            self.is_custom_resized: bool = True
            w: int = int(ev.pos().x())
            h: int = int(ev.pos().y())
            size: tuple[int, int] = max(w, self.min_w), max(h, self.min_h)
            self.resize(*size)
        else:
            super().mouseMoveEvent(ev)

class Scroller(MoveLabel):
    min_w: int = 12
    min_h: int = 50
    top_offset: int = 1
    btm_offset: int = 1
    scroll_down_val: int = 20
    scroll_up_val: int = 25

    def __init__(self, main, showbox, scope_canvas = None, move_canvas = None, top_offset: None | int = None, btm_offset: None | int = None, **kwargs):
        self.top_offset = top_offset or self.top_offset
        self.btm_offset = btm_offset or self.btm_offset
        self.main = main
        self.showbox = showbox
        super().__init__(main, **kwargs)
        self.scope_canvas = scope_canvas or showbox.scope_canvas
        self.move_canvas = move_canvas or showbox.move_canvas
        self.resize(self.min_w, self.min_h)
        self.position()

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

        self.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.setPixmap(pixmap)

    def mousePressEvent(self, *args):
        super().mousePressEvent(*args)
        self.showbox.raise_attached_objects()

    def mouseMoveEvent(self, ev):
        if self.is_grabbed is None:
            return

        min_y: int = self.get_min_y()
        max_y: int = self.get_max_y()

        delta = ev.pos() - self.is_grabbed
        top: int = min(max_y, max(min_y, (self.pos() + delta).y()))
        lft: int = self.geometry().left()

        self.move(lft, top)
        self.cards_follows_scroller()

    def get_max_y(self) -> int:
        return (self.showbox.geometry().bottom() - self.height()) - self.btm_offset

    def get_min_y(self) -> int:
        return self.showbox.geometry().top() + 2 + self.top_offset

    def get_canvas_progress(self) -> float:
        off_chart: int = abs(self.move_canvas.geometry().top())
        rng: int = self.move_canvas.height() - self.scope_canvas.height()
        prog: float = off_chart / max(rng, 1)
        return min(1.0, max(0.0, prog))

    def get_scroller_progress(self) -> float:
        min_y: int = self.get_min_y()
        max_y: int = self.get_max_y()
        now_y: int = self.geometry().top()
        rng: int = max_y - min_y
        prog: float = (now_y - min_y) / max(rng, 1)
        return prog


    def scroll_down(self):
        x: int = self.move_canvas.geometry().left()
        if self.move_canvas.height() <= self.scope_canvas.height():
            if self.move_canvas.geometry().top() != 0:
                self.move_canvas.move(x, 0)
        else:
            now_top: int = self.move_canvas.geometry().top()
            scope_h: int = self.scope_canvas.height()
            now_btm: int = self.move_canvas.geometry().bottom()
            val: int = min(now_btm - scope_h + 2, self.scroll_down_val)
            y: int = now_top - val
            self.move_canvas.move(x, y)

        self.scroller_follows_canvas()

    def scroll_up(self):
        x: int = self.move_canvas.geometry().left()
        if self.move_canvas.height() <= self.scope_canvas.height():
            if self.move_canvas.geometry().top() != 0:
                self.move_canvas.move(x, 0)
            if self.geometry().top() != self.get_min_y():
                self.move(self.geometry().left(), self.get_min_y())
        else:
            now_top: int = self.move_canvas.geometry().top()
            y: int = min(0, now_top + self.scroll_up_val)
            self.move_canvas.move(x, y)

        self.scroller_follows_canvas()

    def cards_follows_scroller(self):
        prog1: float = self.get_scroller_progress()
        prog2: float = self.get_canvas_progress()
        diff: float = abs(prog1 - prog2)
        pps: float = (self.move_canvas.height() - self.scope_canvas.height()) / 100
        x: int = self.move_canvas.geometry().left()
        y: int = self.move_canvas.geometry().top()
        delta: float = pps * (diff * 100.0)
        if prog1 < prog2:
            y = min(0, y + int(delta))
            self.move_canvas.move(x, y)
        else:
            y = max(self.scope_canvas.height() - self.move_canvas.height() - 1, y - int(delta))
            self.move_canvas.move(x, y)

    def scroller_follows_canvas(self):
        prog: float = self.get_canvas_progress()
        min_y: int = self.get_min_y()
        max_y: int = self.get_max_y()
        rng: int = max_y - min_y
        y: int = min_y + int(rng * prog)
        x: int = self.geometry().left()
        self.move(x, y)

    def position(self):
        min_y: int = self.get_min_y()
        max_y: int = self.get_max_y()
        rng: int = max_y - min_y
        y: int = min_y + int(rng * self.get_canvas_progress())
        x: int = self.showbox.geometry().right() - (self.min_w // 2)
        self.move(x, y)

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

    def mouseReleaseEvent(self, ev):
        self.reversed: bool = ev.button().value not in [1]
        self.active: bool = not self.active
        self.draw_background_hover()

    def draw_background_idle(self):
        if not self.active:
            text_col: tuple = self.tx_col
            bg_col: tuple = self.bg_col
        else:
            text_col: tuple = add_rgb(*self.tx_col[:3], factor=0.5)
            bg_col: tuple = self.bg_col[:3]
            if all(bg_col[0] == col for col in bg_col[1:]):
                r, g, b = bg_col
                bg_col: tuple = sub(r, factor=0.2), add(g, factor=0.3), sub(b, factor=0.2)
            else:
                bg_col: tuple = add_rgb(*bg_col, factor=0.25)

        self.draw_background(bg_col=bg_col, border_col=self.border_col)
        self.alter_stylesheet(key='color', val=f'rgb{text_col}')

    def draw_background_hover(self):
        if not self.active:
            text_col: tuple = add_rgb(*self.tx_col[:3], factor=0.25)
            bg_col: tuple = add_rgb(*self.bg_col[:3], factor=0.45)
        else:
            text_col: tuple = add_rgb(*self.tx_col[:3], factor=0.5)
            bg_col: tuple = self.bg_col[:3]
            if all(bg_col[0] == col for col in bg_col[1:]):
                bg_col: tuple = bg_col[0], add(bg_col[1], factor=0.55), bg_col[2]
            else:
                bg_col: tuple = add_rgb(*bg_col, factor=0.5)

        border_col: tuple = add_rgb(*self.border_col[:3], factor=1.0)
        self.draw_background(bg_col=bg_col, border_col=border_col)
        self.alter_stylesheet(key='color', val=f'rgb{text_col}')

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


class GroupBTN(ActiveRevBTN):
    var: str = ''
    mode: int = 0
    modes: list[str] = []
    font_size: int = 11
    default: bool = False
    allow_multiple: bool = True
    allow_all_off: bool = False
    def __init__(self, master, group: list | None = None, default: bool = False, allow_multiple: bool = False, allow_all_off: bool = True, modes: list[str] | None = None, **kwargs):
        super().__init__(master, adjustable_fontsize=False, **kwargs)
        self.default : bool = default
        self.allow_multiple: bool = allow_multiple
        self.allow_all_off: bool = allow_all_off
        self.group: list = group if group is not None else []
        self.modes: list[str] = modes or self.modes or [self.var]
        self.group.append(self)

    def save_settings(self):
        """child does this instead of parent"""

    def get_longest_text(self) -> str:
        texts: list[str] = [x for x in self.modes]
        texts.sort(key=len)
        return texts[-1]

    def get_text(self) -> str:
        return self.modes[self.mode]

    def change_mode(self, forward: bool = True):
        if not forward:
            if self.mode == 0:
                self.mode = len(self.modes) - 1
            else:
                self.mode -= 1
        else:
            if self.mode >= len(self.modes) - 1:
                self.mode = 0
            else:
                self.mode += 1

        text: str = self.get_text()
        self.setText(text)

    def mouseReleaseEvent(self, ev):
        forward: bool = ev.button().value in [1]
        self.toggle_btn()
        self.change_mode(forward)
        self.save_settings()

    def toggle_btn(self):
        self.active = not self.active
        if not self.allow_all_off and all(not btn.active for btn in self.group):
            self.active = True

        if not self.allow_multiple and self.active:
            for btn in self.group:
                if not btn.active or btn == self:
                    continue

                btn.active = False
                btn.save_settings()
                btn.draw_background_idle()

        self.draw_background_hover() if self.active else self.draw_background_idle()
