from PIL              import Image
from PIL.ImageDraw    import ImageDraw
from PIL.ImageQt      import ImageQt
from PyQt6            import QtCore, QtGui, QtWidgets
from ui.basics        import Label, MoveLabel, ResizeLabel, Scroller
from ui.basics        import ShadeLabel
from ui.databar       import ActiveRevBTN, SortBTN, Sorters
from ui.deckstatus    import DeckStatus
from ui.fidget        import Fidget, SlotBox
from useful.breakdown import MTG_TYPES, sort_cards
from useful.database  import Card, MTGData, Set
from useful.tech      import add, add_rgb, shrinking_rect, sub, sub_rgb




class RollDownSortBTN(SortBTN):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, adjustable_fontsize=False, *args, **kwargs)
        self.alter_stylesheet(key='font', val='10px')

    def mouseReleaseEvent(self, ev):
        self.reversed = ev.button().value == 2
        for btn in self.master.sort_btns:
            btn.active = btn == self
            btn.reversed = self.reversed if btn.active else False
            btn.draw_background_hover() if btn.active else btn.draw_background_idle()

        var: str = self.var[self.var.find('_') + 1:].upper()
        save_key: str = self.master.rolldown.get_sort_var()
        self.master.deck[save_key]: tuple[str, bool] = var, self.reversed,
        self.master.rolldown.showbox.save_deck() # lazy hack, also saves sort settings
        self.master.rolldown.sort_fidgets()
        self.master.mouseReleaseEvent(ev)


class RollDownSorters(MoveLabel):
    min_h: int = 30
    settings_var: str = 'type_sorters'
    def __init__(self, main, rolldown, **kwargs):
        self.rolldown = rolldown
        self.sort_btns: list[SortBTN] = []
        self.main = main
        self.databar = rolldown.databar
        self.searchbox = rolldown.showbox
        self.deck = rolldown.deck
        super().__init__(main, **kwargs)
        self.name = RollDownSortBTN(self, var='sort_name')
        self.rarity = RollDownSortBTN(self, var='sort_rarity')
        self.cmc = RollDownSortBTN(self, var='sort_cmc')
        self.color = RollDownSortBTN(self, var='sort_color')
        self.power = RollDownSortBTN(self, var='sort_power')
        self.toughness = RollDownSortBTN(self, var='sort_toughness')
        self.amount = RollDownSortBTN(self, var='sort_amount')

        self.set_active_button()

    def set_active_button(self):
        var, rev = self.deck.get(self.rolldown.get_sort_var(), None) or ('CMC', False,)
        for btn in self.sort_btns:
            btn.active = var.lower() in btn.var.lower()
            btn.reversed = rev if btn.active else False
            btn.draw_background_hover() if btn.active else btn.draw_background_idle()

class TypeAmounts(Label):
    min_w: int = 70
    color_rgb: tuple = 220,220,220
    def __init__(self, master, **kwargs):
        self.databar = master
        self.showbox = master.showbox
        self.fidgets = master.fidgets
        self.deck = master.deck
        self.rolldown = master.rolldown
        self.color_rgb = add_rgb(*self.databar.title.color_rgb, factor=0.0)
        super().__init__(master, **kwargs)
        self.background = Label(self)
        self.textlabel = ShadeLabel(self)
        self.textlabel.setStyleSheet(f'background:transparent;color:rgb{self.color_rgb};font:20px')
        self.textlabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignRight)
        for label in [self.textlabel.shadelabel, self.textlabel.textlabel]:
            label.setContentsMargins(0,0,10,0)

        self.update_text()
        self.resize(self.min_w, self.databar.min_h)

    def resizeEvent(self, a0):
        w, h = self.width(), self.height()
        [obj.resize(w, h) for obj in (self.background, self.textlabel)]

        bg_col: tuple = 0,0,0,0

        args: tuple = 'RGBA', (w, h), bg_col
        im = Image.new(*args)
        draw = ImageDraw(im)

        rgb, a = (90, 90, 90), 255
        for n in range(3):
            draw.line(xy=(n, h - 3, n + 10, 1), fill=(*rgb, a))
            rgb = sub_rgb(*rgb, min_sub=5)

        for n in range(3, 4):
            draw.line(xy=(n, h - 3, n + 10, 1), fill=(0,0,0,255))

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

    def update_text(self):
        self.textlabel.setText(self.get_amount_str())

    def get_amount(self) -> int:
        amounts: int = sum(fidget.get_amounts() for _, fidget in self.fidgets.items()) if self.fidgets else 0
        return amounts

    def get_amount_str(self) -> str:
        return str(self.get_amount())


class Title(Label):
    min_w: int = 100
    color_rgb: tuple = 255, 255, 255
    def __init__(self, master, **kwargs):
        self.databar = master
        self.showbox = master.showbox
        self.fidgets = master.fidgets
        self.deck = master.deck
        self.rolldown = master.rolldown
        super().__init__(master, **kwargs)
        self.textlabel = ShadeLabel(self)
        self.textlabel.setStyleSheet(f'background:transparent;color:rgb{self.color_rgb};font:20px;font-weight:600')

        for label in [self.textlabel.textlabel, self.textlabel.shadelabel]:
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
            label.setContentsMargins(10, 0, 0, 0)

        self.textlabel.setText(self.get_title_str())
        self.resize(self.min_w, self.databar.min_h)

    def get_title_str(self) -> str:
        var: str = self.master.master.card_type
        return (f'{var[:-1]}ies' if var.endswith('y') else f'{var}s').upper()

    def resizeEvent(self, a0):
        w, h = self.width(), self.height()
        [obj.resize(w, h) for obj in (self.textlabel,)]
        var: str = self.get_title_str()
        self.textlabel.setText(var)
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

class RollDownDataBar(Label):
    min_h: int = 30
    rolldown_sorter: None | RollDownSorters = None
    def __init__(self, master, **kwargs):
        self.main = master.main
        self.deck = master.deck
        self.fidgets = master.fidgets
        self.showbox = master.showbox
        self.rolldown = master
        super().__init__(master, **kwargs)
        self.background = Label(self)
        self.title = Title(self)
        self.amounts = TypeAmounts(self)

    def expand(self):
        w: int = max(self.title.min_w, self.title.textlabel.get_text_width() + 20)
        self.title.resize(w, self.min_h)
        tw: int = self.title.textlabel.width()
        aw: int = self.amounts.textlabel.width()
        fw: int = 0
        for _, fidget in self.fidgets.items():
            fw = max(fidget.get_min_width(), fw)

        w = max(tw + aw + 50, fw)
        self.amounts.move(w - aw, 0)
        self.resize(w, self.min_h)

    def open_close_sortbox(self):
        for _, rolldown in self.showbox.deckdetails.types.items():
            if rolldown.databar.rolldown_sorter:
                try:
                    rolldown.databar.rolldown_sorter.close()
                finally:
                    rolldown.databar.rolldown_sorter = None
                    if rolldown == self.rolldown:
                        return

        self.rolldown_sorter = RollDownSorters(self.main, self.rolldown)
        self.rolldown_sorter.show()

        btns: list = self.rolldown_sorter.sort_btns
        h: int | None = None
        for btn in btns:
            text: str = btn.var.split('_')[-1].upper()
            btn.setText(text)
            w: int = btn.get_text_width() + 10
            h = h if h is not None else (btn.get_text_height() + 8)
            btn.resize(w, h)

        max_w: int = sum(btn.width() for btn in btns)
        cent: int = max_w // 2
        x: int = 0
        y: int = 0
        for btn in btns:
            w: int = btn.width()
            if not y and (x + w > cent + (w // 2)):
                y += btn.height() - 1
                x = 0
            btn.move(x, y)
            x += btn.width() - 1

        row1 = [btn for btn in btns if btn.geometry().top() == 0]
        row2 = [btn for btn in btns if btn not in row1]

        max_w1 = sum(btn.width() for btn in row1)
        max_w2 = sum(btn.width() for btn in row2)

        smalls = row1 if max_w1 < max_w2 else row2
        diff = abs(max_w1 - max_w2)
        each = diff // len(smalls)
        rest = diff - (each * len(smalls))
        x: int = 0
        for btn in smalls:
            add_w = each + (1 if rest > 0 else 0)
            w = btn.width() + add_w
            btn.setGeometry(x, btn.geometry().top(), w, h)
            x += w - 1
            rest -= 1

        width: int = x
        height: int = h * 2
        lft: int = self.rolldown.geometry().left()
        top: int = self.rolldown.geometry().top() - height
        if self.rolldown.width() - width > 0:
            lft += (self.rolldown.width() - width) // 2

        self.rolldown_sorter.setGeometry(lft, top, width, height)

    def mouseReleaseEvent(self, ev):
        if ev.button().value != 1:
            self.open_close_sortbox()
        else:
            self.rolldown.save_coords()


    def resizeEvent(self, a0):
        w, h = self.width(), self.height()
        self.background.resize(w, h)
        self.draw_background_idle()

    def draw_background_hover(self):
        wall: int = self.amounts.geometry().left()
        w, h = self.width(), self.height()
        bg_col: tuple = 110, 110, 110, 255

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

        r, g, b, a = 20, 20, 20, 255
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
        bg_col: tuple = 90, 90, 90, 255

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

        r, g, b, a = 20, 20, 20, 255
        for n in range(3):
            xy: tuple = shrinking_rect(n, *im.size)
            draw.rectangle(xy, outline=(r, g, b, a))
            r, g, b = add_rgb(r, g, b, min_add=25)

        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)

class TypeRollDown(MoveLabel):
    settings_var: str = 'TypeRollDown!'
    def __init__(self, main, showbox, card_type: str, **kwargs):
        self.card_type: str = card_type
        self.showbox = showbox
        self.deck = self.showbox.deck
        self.settings_var += f' {self.deck.get("uuid", 0.0)} {card_type}'
        self.main = main
        self.fidgets: dict[str, Fidget] = {}
        super().__init__(main, **kwargs)
        self.databar = RollDownDataBar(self)
        self.title = self.databar.title
        self.amounts = self.databar.amounts

        geo: None | tuple = self.get_saved_coords()
        self.move(*geo) if geo else ...

    def resizeEvent(self, a0):
        if self.width() > 40:
            w: int = self.width()
            aw: int = self.amounts.textlabel.width()
            self.amounts.move(w - aw, 0)
            self.databar.resize(w, self.databar.min_h)
            self.sort_fidgets()

    def get_saved_coords(self) -> tuple | None:
        try:
            lft, top = self.deck['rolldowns_geo'][self.card_type][:2]
        except (TypeError, KeyError):
            ...
        else:
            lft = min(self.main.width() - 50, lft)
            top = min(self.main.height() - 50, top)
            return max(50, lft), max(0, top)

    def get_sort_var(self) -> str:
        return f'{RollDownSorters.settings_var} {self.card_type}'

    def save_coords(self):
        geo = self.geometry()
        coords: tuple = geo.left(), geo.top(), geo.right(), geo.bottom()

        if 'rolldowns_geo' not in self.deck or not self.deck['rolldowns_geo']:
            self.deck['rolldowns_geo'] = {}

        self.deck['rolldowns_geo'][self.card_type]: tuple = coords
        self.showbox.save_deck()

    def get_sorted_fidgets(self) -> list[Fidget]:
        fidgets: list[Fidget] = [v for _, v in self.fidgets.items() if v]
        var, rev = self.deck.get(self.get_sort_var(), None) or ('CMC', False,)
        cards: list = [dict(card=x.card_data, fidget=x) for x in fidgets]
        if var in 'AMOUNT':
            cards.sort(key=lambda x:x['fidget'].get_amounts(), reverse=rev)
        else:
            sort_cards(cards, var=var, reverse=rev)
            if var in 'CMC' and self.card_type in 'Land':
                basics: list = [bag for bag in cards if 'Basic Land' in (bag['card'][Card.type] or '')]
                others: list = [bag for bag in cards if bag not in basics]
                cards = basics + others

        return [x['fidget'] for x in cards]

    def sort_fidgets(self):
        w: int = self.databar.width()
        y: int = self.databar.geometry().bottom()
        fidgets: list[Fidget] = self.get_sorted_fidgets()
        for fidget in fidgets:
            fidget.setGeometry(0, y, w, fidget.min_h)
            y += fidget.height()

    def expand(self):
        self.databar.expand()
        self.sort_fidgets()
        fidgets: list[Fidget] = self.get_sorted_fidgets()
        w: int = self.databar.width()
        y: int = max(fidget.geometry().bottom() for fidget in fidgets) if fidgets else self.databar.min_h
        self.resize(w, y)
        self.databar.amounts.update_text()

    def enterEvent(self, event):
        self.databar.draw_background_hover()

    def leaveEvent(self, a0):
        self.databar.draw_background_idle()

    def closeEvent(self, a0):
        if self.databar.rolldown_sorter:
            try:
                self.databar.rolldown_sorter.close()
            finally:
                self.databar.rolldown_sorter = None


class DeckDetails(MoveLabel):
    type_prio: dict[str, int] = {}
    fixed_rolldown_width: bool = True
    fixed_rolldown_alignment: bool = True
    arm_lenght: int = RollDownDataBar.min_h * 2
    gap_size: int = 5
    min_h: int = int(RollDownDataBar.min_h * 1.2)
    min_w: int = 100
    settings_var: str = 'all deckdetails'
    var: str = 'deckdetails on/off'
    mouse_btn: int | None = None

    def __init__(self, main, showbox, **kwargs):
        self.main = main
        self.showbox = showbox
        self.cards: list[dict] = self.showbox.cards
        self.deck: dict = self.showbox.deck
        self.attached_objects: list = []
        self.types: dict[str, TypeRollDown] = {}
        super().__init__(main, **kwargs)
        self.background = Label(self)
        self.deck_status = DeckStatus(self)

        geo: None | tuple = self.get_saved_coords()
        self.move(*geo or (50, 50,))

    def mousePressEvent(self, ev):
        self.mouse_btn = 1 if ev.button().value == 1 else 2
        self.is_grabbed = ev.pos()
        self.raise_()

    def mouseMoveEvent(self, ev):
        x1, y1 = self.geometry().x(), self.geometry().y()
        super().mouseMoveEvent(ev)
        if self.mouse_btn == 2:
            x2, y2 = self.geometry().x(), self.geometry().y()
            x_add, y_add = x1 - x2, y1 - y2
            for rd in [rolldown for _, rolldown in self.types.items()]:
                rd.move(rd.geometry().left() - x_add, rd.geometry().top() - y_add)

    def mouseReleaseEvent(self, ev):
        super().mouseReleaseEvent(ev)
        self.save_coords()
        [rolldown.save_coords() for _, rolldown in self.types.items()] if self.mouse_btn == 2 else ...
        self.mouse_btn = None

    def get_saved_coords(self) -> tuple | None:
        try:
            lft, top = self.deck['rolldowns_geo'][self.settings_var][:2]
        except (TypeError, KeyError):
            ...
        else:
            lft = min(self.main.width() - 50, lft)
            top = min(self.main.height() - 50, top)
            return max(50, lft), max(0, top)

    def save_coords(self):
        geo = self.geometry()
        coords: tuple = geo.left(), geo.top(), geo.right(), geo.bottom()

        if 'rolldowns_geo' not in self.deck or not self.deck['rolldowns_geo']:
            self.deck['rolldowns_geo'] = {}

        self.deck['rolldowns_geo'][self.settings_var]: tuple = coords
        self.showbox.save_deck()

    def update_status(self):
        self.deck_status.update_status()

        h: int = self.min_h
        x: int = self.deck_status.geometry().right()

        self.resize(x + 2, h)
        self.raise_()

    def resizeEvent(self, a0):
        w, h = self.width(), self.height()
        [obj.resize(w, h) for obj in (self.background,)]


    def closeEvent(self, a0):
        for _, rolldown in self.types.items():
            try:
                rolldown.close()
            except:
                ...

    def get_type_prio(self) -> dict:
        if not self.type_prio:
            first: tuple = 'Planeswalker', 'Land', 'Creature', 'Artifact', 'Enchantment', 'Battle'
            last: tuple = 'Tribal', 'Kindred'
            card_types: list[str] = [f'{x[0].upper()}{x[1:].lower()}' for x in MTG_TYPES]
            for type in list(first) + card_types + list(last):
                if type not in self.type_prio:
                    self.type_prio[type]: int = len(self.type_prio)

        return self.type_prio

    def decide_card_type(self, card_data: tuple) -> str:
        types: list = (card_data[Card.types] or '').split(',')
        type_prio: dict = self.get_type_prio()
        types.sort(key=lambda x: type_prio.get(x, 100))
        type1: str = types[0] if types else ''
        return type1

    def get_slotboxes(self) -> list[SlotBox]:
        slotboxes: list[SlotBox] = []
        if any(not box['showcase'] for box in self.cards):
            return slotboxes

        for box in self.cards:
            showcase = box['showcase']
            if showcase.get_amount() <= 0:
                continue

            card_data: tuple = showcase.card_data
            amount: int = showcase.get_amount()
            slot: str = showcase.slot
            type: str = self.decide_card_type(card_data)
            slotboxes.append(
                SlotBox(amount=amount, card=card_data, slot=slot, type=type, showcase=showcase)
            )

        return slotboxes

    def kill_zero_amounts_fidgets(self):
        kill: set[Fidget] = set()
        for _, rolldown in self.types.items():
            for name, fidget in rolldown.fidgets.items():
                if fidget.get_amounts() <= 0:
                    kill.add(fidget)

        [fidget.close() for fidget in kill]

    def update_typerollers(self):
        self.kill_zero_amounts_fidgets()

        slotboxes: list[SlotBox] = self.get_slotboxes()
        all_types: set[str] = {box['type'] for box in slotboxes}
        now_types: set[str] = set(self.types.keys())
        for t in now_types:
            if t not in all_types:
                self.types[t].close()
                self.types.pop(t)

        for t in all_types:
            if t in self.types:
                continue

            self.create_typeroller(var=t)

        for box in slotboxes:
            showcase = box['showcase']
            rolldown = self.types[box['type']]
            name: str = showcase.card_data[Card.name]
            if name in rolldown.fidgets:
                fidget = rolldown.fidgets[name]
                fidget.showcases.add(showcase)
                fidget.update_text()
            else:
                fidget = Fidget(rolldown, showcase)
                rolldown.fidgets[name] = fidget
                fidget.show()

        self.edge_case_thingey() # can be removed if you feel like it
        self.sweet_rolldown_positioning()

    def get_rolldown_blocks(self) -> list[list[TypeRollDown]]:
        """makes a list with lists of rolldowns where user seesm to have them vertically aligned after each others"""
        rolldowns: set[TypeRollDown] = {rolldown for _, rolldown in self.types.items()}
        arm: int = self.arm_lenght

        blocks: list = []
        while rolldowns:
            block: list = [next(iter(rolldowns))]
            rolldowns.remove(block[0])

            while rolldowns:
                top: int = min(x.geometry().top() for x in block)
                btm: int = max(x.geometry().bottom() for x in block)
                lft: int = min(x.geometry().left() for x in block)
                rgt: int = max(x.geometry().right() for x in block)

                for rd in rolldowns:
                    x1: int = rd.geometry().left()
                    x2: int = rd.geometry().right()
                    y1: int = rd.geometry().top()
                    y2: int = rd.geometry().bottom()

                    hor_match: bool = x1 - arm < lft < x1 + arm
                    hor_match = hor_match and x2 - arm < rgt < x2 + arm

                    ver_match: bool = top - arm < y2 < top + arm
                    ver_match = ver_match or btm - arm < y1 < btm + arm

                    if hor_match and ver_match:
                        block.append(rd), rolldowns.remove(rd)
                        break
                else:
                    break

            block.sort(key=lambda x: x.geometry().top())
            blocks.append(block)

        blocks.sort(key=lambda _block: min(x.geometry().top() for x in _block))
        blocks.sort(key=lambda _block: min(x.geometry().left() for x in _block))
        return blocks

    def sweet_rolldown_positioning(self):
        rolldowns: set[TypeRollDown] = {rolldown for _, rolldown in self.types.items()}
        if self.fixed_rolldown_width and rolldowns:
            [rolldown.expand() for rolldown in rolldowns]
            least_width: int = max(x.databar.width() for x in rolldowns)
            [x.resize(least_width, x.height()) for x in rolldowns if least_width != x.width()]

        if not self.fixed_rolldown_alignment:
            return

        arm: int = self.arm_lenght
        blocks: list[list[TypeRollDown]] = self.get_rolldown_blocks()

        fixed: list = []
        while blocks:
            block: list = blocks[0]
            curr_top: int  = block[0].geometry().top()
            curr_lft: int = block[0].geometry().left()
            for prev in fixed:
                prev_top: int = prev[0].geometry().top()
                prev_rgt: int = prev[0].geometry().right()

                hor_match: bool = prev_rgt - arm < curr_lft < prev_rgt + arm
                ver_match: bool = prev_top - arm < curr_top < prev_top + arm

                if hor_match and ver_match:
                    top: int = prev_top
                    lft: int = prev_rgt + self.gap_size
                    break
            else:
                top: int = curr_top
                lft: int = curr_lft

            for rd in block:
                rd.move(lft, top)
                top += rd.height() + self.gap_size

            fixed.append(block)
            blocks.remove(block)


    def create_typeroller(self, var: str):
        self.types[var] = TypeRollDown(self.main, self.showbox, card_type=var)
        self.types[var].show()
        self.types[var].expand()

    def update_fidgets(self):
        self.update_typerollers()
        self.update_status()

        rolldowns: list = [rolldown for _, rolldown in self.types.items()]

        x: int = 50
        y: int = 50
        for rolldown in rolldowns:
            if rolldown.get_saved_coords():
                continue

            if x + rolldown.width() > self.main.width():
                x = 50
                y = min(self.main.height() - 50, y + 50)

            rolldown.move(x, y)
            x += rolldown.width() + 5

    def edge_case_thingey(self):
        # if holding multiple showcases and one of them was closed from showbox could trigger crash
        # when showcase.deleteLater() evetually triggers, therefore purging that one hinders crash.
        # removing this part of the loop shouldn't really cause any harm at shorter runtimes.
        for _, rolldown in self.types.items():
            for _, fidget in rolldown.fidgets.items():
                if len(fidget.showcases) > 1:
                    for showcase in fidget.showcases:
                        if showcase.get_amount() <= 0:
                            fidget.showcases.remove(showcase)
                            break

class DeckDetailsBTN(ActiveRevBTN):
    var: str = 'SHOW DECKDETAILS'
    def mouseReleaseEvent(self, ev):
        self.open_close()

    def open_close(self):
        self.active = not self.active
        showbox = self.master.master
        showbox.deck[self.var]: bool = self.active
        showbox.save_deck()
        if showbox.deckdetails is not None:
            try:
                showbox.deckdetails.close()
            finally:
                showbox.deckdetails = None
                return
        else:
            showbox.deckdetails = DeckDetails(showbox.main, showbox=showbox)
            showbox.deckdetails.update_fidgets()
            showbox.deckdetails.show()

        self.draw_background_hover()
