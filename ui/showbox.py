import time
from useful.database import MTGData
from PIL               import Image
from PIL.ImageDraw     import ImageDraw
from PIL.ImageQt       import ImageQt
from PyQt6             import QtCore, QtGui, QtWidgets
from cardgeo.cardgeo   import CardGeo
from ui.basics         import Label, MoveLabel, ResizeLabel, Scroller
from ui.databar        import DataBar, SearchBar
from ui.showcase       import ShowCase
from useful.breakdown  import SmartVal, search_cards, sort_cards, tweak_query
from useful.database   import Card, Set
from useful.tech       import add, add_rgb, add_rgba, shrinking_rect, sub
from useful.threadpool import custom_thread


class ScopeCanvas(Label):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.background = Label(self)

    def enterEvent(self, event):
        self.draw_background_hover()

    def leaveEvent(self, a0):
        self.draw_background_idle()

    def resizeEvent(self, a0):
        self.background.resize(self.width(), self.height())
        self.draw_background_idle()

    def draw_background_hover(self):
        args: tuple = 'RGBA', (self.background.width(), self.background.height()), (25, 25, 25, 255)
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


    def draw_background_idle(self):
        args: tuple = 'RGBA', (self.background.width(), self.background.height()), (25, 25, 25, 255)
        im = Image.new(*args)
        draw = ImageDraw(im)

        r, g, b, a = 0, 0, 0, 255
        for n in range(3):
            xy: tuple = shrinking_rect(n, im.width, im.height)
            draw.rectangle(xy=xy, outline=(r, g, b, a))
            r, g, b = add_rgb(r, g, b, min_add=50)

        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)

class MoveCanvas(Label):
    offset: int = 4
    def __init__(self, master, **kwargs):
        self.main = master.master.master.master
        self.scope_canvas = master.master
        self.showbox = master.master.master
        super().__init__(master, **kwargs)

    def resizeEvent(self, a0):
        px: int = self.offset
        self.master.setGeometry(0, px, self.scope_canvas.width(), self.scope_canvas.height() - (px * 2))


class ShowBox(ResizeLabel):
    min_w: int = 1024
    min_h: int = 768

    settings_var: str = 'ShowBox!'

    batch_size: int = 20
    queue_size: int = batch_size

    databar: DataBar | None = None
    searchbar: SearchBar | None = None

    raise_time: float = 0.0  # keeps track on which of all decks that are on top when drag_n_dropping

    def __init__(self, master, **kwargs):
        self.main = master
        self.cards: list[dict] = []
        self.attached_objects: list = []
        self.raise_time: float = time.time()
        super().__init__(master, min_w=self.min_w, min_h=self.min_h, **kwargs)
        self.scope_canvas = ScopeCanvas(self)
        self._move_plate = Label(self.scope_canvas)
        self.move_canvas = MoveCanvas(self._move_plate)

        geo = self.main.load_setting(self.settings_var)
        if isinstance(geo, (tuple, list)) and len(geo) == 4 and all(isinstance(x, int) for x in geo):
            main = self.main
            lft, top, w, h = geo
            top = max(0, min(main.height() - 100, top))
            lft = max(0, min(main.width() - 100, lft))
            w = max(self.min_w, min(w, main.width()))
            h = max(self.min_h, min(h, main.height()))
            self.setGeometry(lft, top, w, h)
        else:
            self.setGeometry(100, 100, self.min_w, self.min_h)

        self.scroller = Scroller(self.main, showbox=self, scope_canvas=self._move_plate)
        self.attached_objects.append(self.scroller)
        self.scroller.show()

    def closeEvent(self, a0):
        for obj in self.attached_objects:
            try:
                obj.close()
            except:
                ...
        self.draw_next_card = lambda *args, **kwargs: None

    def raise_attached_objects(self):
        [x.raise_() for x in [self] + self.attached_objects]

    def moveEvent(self, a0):
        self.scroller.position()

    def mousePressEvent(self, *args):
        super().mousePressEvent(*args)
        self.raise_attached_objects()

    def mouseReleaseEvent(self, ev):
        if self.is_grabbed:
            geo = self.geometry()
            geo = geo.left(), geo.top(), geo.width(), geo.height()
            self.main.save_setting(self.settings_var, geo)

        super().mouseReleaseEvent(ev)

    def wheelEvent(self, a0):
        steps: int = a0.angleDelta().y() // 120
        vector: int = steps and steps // abs(steps)  # 0, 1, or -1
        if vector == -1:
            self.scroller.scroll_down()
        elif vector == 1:
            self.scroller.scroll_up()

        self.raise_attached_objects()

    def resizeEvent(self, a0):
        w: int = self.width()
        y: int = 0
        if self.databar:
            self.databar.resize(w, self.databar.min_h)
            y += self.databar.height()

        if self.searchbar:
            self.searchbar.setGeometry(0, y, w, self.databar.min_h)
            y += self.databar.height()

        self.scope_canvas.setGeometry(0, y, w, self.height() - y)

        mv_y: int = self.move_canvas.geometry().top()
        mv_h: int = self.move_canvas.height()
        px: int = self.move_canvas.offset
        self.move_canvas.setGeometry(px, mv_y, w - (px  * 2), mv_h)
        self.scroller.top_offset = self.scope_canvas.geometry().top()
        self.scroller.position()

        h: int = 0
        if self.databar:
            vars: tuple = 'more_btn', 'queue_status', 'sorters', 'card_resizer', 'import_export', 'deck_details'
            objs: list = [getattr(self.databar, var) for var in vars]
            self.min_w = sum(obj.width() + 5 for obj in objs if obj) or self.min_w
            h += self.databar.height() * 2

        if self.searchbar:
            h += self.searchbar.height() * 2

        for obj in self.cards:
            if obj['showcase']:
                h += obj['showcase'].height()
                self.min_h = h
                break
        else:
            self.min_h = max(self.min_h, h + self.card_geo().h)

    def show_queue_status(self):
        self.databar.show_queue_status() if self.databar else ...

    def sort_cards(self):
        for btn in self.databar.sorters.sort_btns if (self.databar and self.databar.sorters) else []:
            if btn.active:
                parts: list = btn.var.split('_')
                var: str = parts[-1].upper()
                sort_cards(self.cards, var=var, reverse=btn.reversed)
                break
        else:
            sort_cards(self.cards)

    def _add_queue(self, queue: list) -> int:
        ids: set[str] = {x['card'][Card.scryfall_id] for x in self.cards}
        added: list[dict] = [x for x in queue if x['card'][Card.scryfall_id] not in ids]
        self.cards += added
        return len(added)

    def add_queue(self, queue) -> int:
        if isinstance(queue, list):
            return self._add_queue(queue)

        elif isinstance(queue, dict):
            return self._add_queue([queue])

        elif isinstance(queue, tuple):
            try:
                bag = MTGData.NAME_BAG[queue[Card.name]]
            except (IndexError, KeyError):
                return -1
            else:
                box = dict(card=queue, showcase=None, bag=bag, slot='maindeck', amount=1)
                return self._add_queue([box])

        elif isinstance(queue, str):
            q: str = 'select * from cards where scryfall_id is (?) and (side is "a" or side is null)'
            v: tuple = queue,
            card_data: tuple | None = MTGData.cursor.execute(q, v).fetchone()
            try:
                bag = MTGData.NAME_BAG[card_data[Card.name]]
            except (IndexError, KeyError, ValueError):
                return -1
            else:
                box = dict(card=card_data, showcase=None, bag=bag, slot='maindeck', amount=1)
                return self._add_queue([box])

        return -1

    def clear_queue(self):
        for n in range(len(self.cards) -1, -1, -1):
            showcase: None | ShowCase = self.cards[n]['showcase']
            if showcase:
                if not showcase.is_fortified:
                    self.cards.pop(n)
                    showcase.close()
            else:
                self.cards.pop(n)

    def clear_canvas(self):
        for n in range(len(self.cards) -1, -1, -1):
            showcase = self.cards[n]['showcase']
            if showcase and not showcase.is_fortified:
                self.cards.pop(n)
                showcase.close()

        showcases: list[ShowCase] = [obj['showcase'] for obj in self.cards if obj['showcase']]
        showcases.sort(key=lambda obj: obj.geometry().left())
        showcases.sort(key=lambda obj: obj.geometry().top())
        self.reposition_these_showcases(showcases)

    def reposition_these_showcases(self, showcases: list[ShowCase]):
        cg: type[CardGeo] = self.card_geo()
        positioned: list = []
        for showcase in showcases:
            if positioned:
                w, h = showcase.width(), showcase.height()
                obj_top: list = [(obj, obj.geometry()) for obj in positioned]
                obj_top.sort(key=lambda obj: obj[1].left(), reverse=True)
                obj_top.sort(key=lambda obj: obj[1].top(), reverse=True)
                most_down = obj_top[0][0]
                geo = most_down.geometry()
                top, btm, rgt = geo.top(), geo.bottom(), geo.right()
                y: int = top
                x: int = rgt + cg.offset
                if x + w > self.move_canvas.width() - cg.bleed:
                    y: int = btm + cg.offset
                    x: int = cg.bleed
            else:
                x: int = cg.bleed
                y: int = cg.bleed

            showcase.move(x, y)
            positioned.append(showcase)

    def adjust_move_canvas_height(self):
        showcases: list[ShowCase] = [obj['showcase'] for obj in self.cards if obj['showcase']]
        w, h = self.move_canvas.width(), max(obj.geometry().bottom() for obj in showcases) if showcases else 0
        new_h: int = max(self.scope_canvas.height(), h + self.card_geo().bleed)
        self.move_canvas.resize(w, new_h)

    def adjust_scrollers_scope(self):
        scrope_h: int = self.scope_canvas.height()
        if self.move_canvas.geometry().bottom() < scrope_h:
            lft: int = self.move_canvas.geometry().left()
            self.move_canvas.move(lft, 0)
            self.scroller.scroller_follows_canvas()

    def is_drawing(self) -> bool:
        return self.queue_size != self.batch_size

    def reset_queue_size(self, batch_size: int | None = None):
        self.queue_size = min(1024, batch_size or self.batch_size)

    def extend_queue_size(self):
        self.queue_size += self.batch_size

    def new_showcase(self, box: dict) -> ShowCase:
        return ShowCase(self.move_canvas, card_data=box['card'], bag=box['bag'])

    def new_row_needed(self) -> bool:
        showcases: list[ShowCase] = [obj['showcase'] for obj in self.cards if obj['showcase']]
        if showcases:
            w, h = showcases[0].width(), showcases[0].height(),
            obj_top: list = [(obj, obj.geometry()) for obj in showcases]
            obj_top.sort(key=lambda obj: obj[1].left(), reverse=True)
            obj_top.sort(key=lambda obj: obj[1].top(), reverse=True)
            most_down = obj_top[0][0]
            top, rgt = most_down.geometry().top(), most_down.geometry().right()
            for showcase in showcases:
                if showcase.geometry().right() <= rgt:
                    continue
                elif showcase.geometry().bottom() - (h // 5) > top:
                    return True
            else:
                x: int = rgt + self.card_geo().offset
                if x + w > self.move_canvas.width() - self.card_geo().bleed:
                    return True
        return False

    def insert_card_into_box(self, scryfall_id: str, *args, **kwargs):
        val: int = self.add_queue(scryfall_id)
        if val != -1:
            self.draw_next_card(specific=scryfall_id)
            if val == 0:
                for box in self.cards:
                    showcase = box['showcase']
                    if showcase and scryfall_id in box['card'][Card.scryfall_id]:
                        showcase.center_into_scrollarea()
            else:
                xy: tuple = self.scroller.geometry().left(), self.scroller.get_max_y()
                self.scroller.move(*xy)
                self.scroller.cards_follows_scroller()

    def card_geo(self) -> type[CardGeo]:
        if self.databar and self.databar.card_resizer:
            return self.databar.card_resizer.card_geo
        else:
            return CardGeo

    def draw_next_card(self, specific: str = ''):
        cg: type[CardGeo] = self.card_geo()
        for box in self.cards:
            card: tuple = box['card']
            scryfall_id: str = card[Card.scryfall_id]
            if box['showcase'] or specific not in scryfall_id:
                continue
            else:
                self.queue_size -= 1

            showcases: list[ShowCase] = [obj['showcase'] for obj in self.cards if obj['showcase']]
            if showcases:
                obj_top: list = [(obj, obj.geometry()) for obj in showcases]
                obj_top.sort(key=lambda obj: obj[1].left(), reverse=True)
                obj_top.sort(key=lambda obj: obj[1].top(), reverse=True)
                most_down = obj_top[0][0]
                geo = most_down.geometry()
                top, btm, lft, rgt = geo.top(), geo.bottom(), geo.left(), geo.right()
                for showcase in showcases:
                    if showcase.geometry().right() <= rgt:
                        continue
                    elif showcase.geometry().bottom() - (cg.h // 5) > top:
                        y: int = btm + cg.offset
                        x: int = cg.bleed
                        break
                else:
                    y: int = top
                    x: int = rgt + cg.offset
                    if x + cg.w > self.move_canvas.width() - cg.bleed:
                        y: int = btm + cg.offset
                        x: int = cg.bleed
            else:
                x: int = cg.bleed
                y: int = cg.bleed

            if (self.new_row_needed() and self.queue_size < 0) or self.queue_size < -100:
                if not specific: # specific always passes through
                    break

            box['showcase'] = self.new_showcase(box)
            showcase = box['showcase']
            showcase.setGeometry(x, y, cg.w, cg.h)
            showcase.draw_background()
            showcase.set_image()
            showcase.show()

            self.show_queue_status()
            self.adjust_move_canvas_height()

            if self.new_row_needed():
                custom_thread(lambda: self.draw_next_card(specific=specific), delay=0.01)
                return

        self.adjust_move_canvas_height()
        self.adjust_scrollers_scope()
        self.show_queue_status()
        self.reset_queue_size()