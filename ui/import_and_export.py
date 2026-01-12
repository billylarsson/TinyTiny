from json import JSONDecodeError

from PIL               import Image
from PIL.ImageDraw     import ImageDraw
from PIL.ImageQt       import ImageQt
from PyQt6             import QtCore, QtGui, QtWidgets
from copy              import deepcopy
from ui.basics         import Label, MoveLabel
from ui.databar        import ActiveRevBTN, DataBar
from useful.breakdown  import BoolKey, SmartKey, search_cards, smartkeys
from useful.breakdown  import tweak_query
from useful.database   import Card, MTGData, Owned, card_owned, name_owned
from useful.tech       import add, add_rgb, alter_stylesheet, shrinking_rect
from useful.tech       import sub, sub_rgb
from useful.threadpool import custom_thread
import json, time
from ui.basics import GroupBTN


class DeckItem(dict):
    slot: str
    amount: int
    card_data: tuple
    card_name: str
    fixed_setcode: bool
    own_card: bool | None
    own_name: bool | None

def deck_item(card_data: tuple, amount: int = 1, slot: str = 'maindeck', fixed_setcode: bool = False) -> DeckItem:
    card_name: str = card_data[Card.name]
    return DeckItem(
        slot=slot,
        amount=amount,
        card_data=card_data,
        fixed_setcode=fixed_setcode,
        card_name=card_name,
        own_card=None,
        own_name=None,
    )


class PlainTextEdit(QtWidgets.QPlainTextEdit):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.setStyleSheet('background:transparent;color:white;font:11px')
        self.setFont(QtGui.QFont('monospace'))
        scrollbar = QtWidgets.QScrollBar(self)
        scrollbar.setStyleSheet('background:transparent;width:0px')
        self.setVerticalScrollBar(scrollbar)

        scrollbar = QtWidgets.QScrollBar(self)
        scrollbar.setStyleSheet('background:rgb(150,150,150);height:5px')
        self.setHorizontalScrollBar(scrollbar)
        self.show()

class TextInOutThingey(Label):
    min_h: int = 500
    bg_col: tuple = 0, 0, 0, 255
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.background = Label(self)
        self.textedit = PlainTextEdit(self)

    def resizeEvent(self, a0):
        w, h = self.width(), self.height()
        [obj.resize(w, h) for obj in (self.background, self.textedit,)]
        self.textedit.setGeometry(4, 4, w - 8, h - 8)
        self.draw_background_idle()

    def enterEvent(self, event):
        self.draw_background_hover()

    def leaveEvent(self, event):
        self.draw_background_idle()

    def draw_background_hover(self):
        w, h = self.background.width(), self.background.height()
        args: tuple = 'RGBA', (w, h), self.bg_col
        im = Image.new(*args)
        draw = ImageDraw(im)

        rgb: tuple = 165,165,165
        for n in range(1, 3):
            draw.rectangle(xy=shrinking_rect(n, *im.size), outline=rgb)
            rgb = sub_rgb(*rgb, factor=0.25)

        for n in [0, 3]:
            draw.rectangle(xy=shrinking_rect(n, *im.size), outline=(0, 0, 0))

        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)

    def draw_background_idle(self):
        w, h = self.width(), self.height()

        args: tuple = 'RGBA', (w, h), self.bg_col
        im = Image.new(*args)
        draw = ImageDraw(im)

        rgb: tuple = 150,150,150
        for n in range(1, 3):
            draw.rectangle(xy=shrinking_rect(n, *im.size), outline=rgb)
            rgb = sub_rgb(*rgb, factor=0.25)

        for n in [0, 3]:
            draw.rectangle(xy=shrinking_rect(n, *im.size), outline=(0, 0, 0))

        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)

class TextPOut(TextInOutThingey):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

class FreeHand(TextInOutThingey):
    delay: float = 0.1
    next_run: float = 0.0
    bg_col: tuple = 25, 35, 25, 255
    prev_searches: dict = {}
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.textedit.textChanged.connect(self.text_changed)

    def get_rowbag(self) -> dict[int, DeckItem | None]:
        user_input: str = self.textedit.toPlainText()
        return self.rowbag_from_text(user_input)

    def text_changed(self, is_runner: bool = False, *args, **kwargs):
        # search will start after a small delay from the most recent keystroke
        if not self.master.auto_update():
            return

        search_now: bool = is_runner and 0.0 < self.next_run < time.time()
        if not search_now:
            restart_runner: bool = self.next_run <= 0.0 or is_runner
            self.next_run = time.time() + self.delay
            custom_thread(lambda: self.text_changed(is_runner=True), delay=self.delay) if restart_runner else ...
        else:
            self.next_run = 0.0
            self.master.show_everything_on_demand()


    def extract_number(self, text: str, first_always_digit: bool = True) -> int | None:
        num: str = ''
        for ix, char in enumerate(text):
            if char.isdigit():
                num += char
            else:
                if ix == 0 and first_always_digit:
                    break
                elif num:
                    num: str = ''
                    break

        return int(num) if num else None

    def remodified_text_with_correct_slashes(self, text: str) -> str:
        lft: str = ''
        rgt: str = ''
        text = text.strip()
        while text.startswith('/'):
            lft += '/'
            text = text[1:].lstrip()
        while text.endswith('/'):
            rgt += '/'
            text = text[:-1].rstrip()

        blocks: list[str] = text.split('/')
        mid: str = ' // '.join(x for x in blocks if x.strip())
        return ' '.join(f'{lft} {mid} {rgt}'.split())


    def remodified_text_cut_from_myster_list_etc(self, text: str) -> str:
        for stupid_setcode in ['PLST', 'MB1', 'MB2', 'CMB1', 'CMB2']:
            stupid_setcode = f'({stupid_setcode})'
            if stupid_setcode in text:
                text = text[:text.find(stupid_setcode)]
        return text

    def remodified_text_with_setcode_expansion(self, text: str) -> str:
        ix1: int = text.find('(')
        ix2: int = text.find(')')
        if ix1 != -1 and ix2 > ix1:
            ab: tuple = ' ', '_'
            word: str = text[ix1 + 1: ix2].replace(*ab)
            if len(word) in [3] and word[0].isalpha() and word.isupper():
                word = 'setcode=' + word
            elif word and word[0].isupper() and word[0].isalpha() and any(x.islower() and x.isalpha() for x in word):
                word = 'expansion=' + word
            else:
                word = ''

            text = text[:ix1] + f' {word} ' + text[ix2 + 1:]
        else:
            parts: list[str] = [x for x in text.split() if x.strip()]
            for ix, part in enumerate(parts):
                if len(part) in [3] and part[0].isalpha() and part.isupper():
                    parts[ix]: str = f'setcode={part}'
                    text = ' '.join(parts)
                    break
        return text

    def remodify_number_into_parts(self, parts: list[str]) -> None:
        for ix, part in enumerate(parts[1:], start=1):
            if part[0].isdigit():
                number: int | None = self.extract_number(part)
                if number is not None:
                    parts[ix]: str = f'number={self.extract_number(part)}'
                else:
                    parts[ix]: str = ' '

    def remodify_void_surrounding_stars(self, parts: list[str]) -> None:
        for n, part in enumerate(parts):
            if part.startswith('*') and part.endswith('*'): # clears moxfield *F*
                parts[n]: str = ' '

    def remodify_upper_and_lower_into_parts(self, parts: list[str]) -> None:
        for ix, part in enumerate(parts):
            if part in ['M', 'R', 'U', 'C']:
                parts[ix]: str = part.upper()
            else:
                parts[ix]: str = part.lower()

    def extracted_amount_from_parts(self, parts: list[str]) -> int:
        amount: int = 1
        for ix, part in enumerate(parts[:1]):
            if part[0].isdigit():
                num_none: int | None = self.extract_number(part.rstrip('xX'))
                if num_none is not None:
                    parts[ix]: str = ' '
                    amount = int(num_none)
                break

        return amount

    def get_slot(self, prev_slot: str, text: str) -> str:
        if prev_slot in ['commander', 'companion']:
            return 'maindeck'

        text: str = text.lower().strip(':')
        for slot in self.master.deckbox.deckslots:
            if text == slot:
                return slot

        return prev_slot

    def json_decode(self, text: str) -> str:
        if 0 < text.count('{') == text.count('}'):
            try:
                box: dict = json.loads(text)
            except JSONDecodeError:
                return text
            else:
                if 'scry_card' not in dir(self):
                    q: str = 'select * from cards where side is "a" or side is null'
                    self.scry_card: dict = {x[Card.scryfall_id]: x for x in MTGData.cursor.execute(q).fetchall()}

                rows: list[str] = []
                skipped = 0
                for some_slot in box:
                    for real_slot in self.master.deckbox.deckslots:
                        if real_slot == some_slot:
                            rows.append(f'{real_slot.upper()}:')
                            break
                    else:
                        rows.append('MAINDECK:')

                    for scry, amount in box[some_slot].items():
                        if not isinstance(scry, str) or not isinstance(amount, int):
                            continue
                        elif scry not in self.scry_card:
                            skipped += 1
                            continue

                        card_data: tuple = self.scry_card[scry]
                        card_name: str = card_data[Card.name]
                        card_number: str = card_data[Card.number] or ""
                        setcode: str = card_data[Card.setcode]
                        rows.append(f'{amount}x {card_name} ({setcode}) {card_number}')

                if len(rows) > skipped:
                    text = '\n'.join(rows)

        return text

    def rowbag_from_text(self, user_input: str) -> dict[int, DeckItem | None]:
        user_input = self.json_decode(text=user_input)

        ab: tuple = '\t', ' '
        rows: list[str] = [x.replace(*ab) for x in user_input.split('\n')]
        rows = [x.strip() for x in rows if x.strip()]
        row_bag: dict[int, DeckItem | None] = {}
        cust_smks: list[SmartKey] = [x for x in smartkeys if not isinstance(x, BoolKey)]
        slot: str = 'maindeck'

        for row_num, org_text in enumerate(rows):
            text: str = org_text
            if org_text not in self.prev_searches:
                text = self.remodified_text_cut_from_myster_list_etc(text)
                text = self.remodified_text_with_correct_slashes(text)
                text = self.remodified_text_with_setcode_expansion(text)
                parts: list[str] = [x for x in text.split() if x.strip()]
                amount: int = self.extracted_amount_from_parts(parts)

                self.remodify_number_into_parts(parts)
                self.remodify_void_surrounding_stars(parts)
                self.remodify_upper_and_lower_into_parts(parts)
                text = ' '.join(' '.join(parts).split())
            else:
                amount: int = self.extracted_amount_from_parts(text.split())

            slot: str = self.get_slot(prev_slot=slot, text=text)
            if text in self.prev_searches:
                item: DeckItem | None = deepcopy(self.prev_searches[text])
                if item:
                    item['amount']: int = amount
            else:
                item: DeckItem | None = None
                if len(self.prev_searches) > 5000:
                    self.prev_searches = {}

                purges: list[str] = ['setcode=', 'number=']
                for tmp_txt in [text, ' '.join(x for x in text.split() if all(not x.startswith(y) for y in purges))]:
                    if item is not None or not tmp_txt:
                        continue

                    for smks in [smartkeys, cust_smks]:
                        tweaked_text: str = tweak_query(tmp_txt, custom_smartkeys=smks)
                        queue: list = search_cards(tweaked_text, custom_smartkeys=smks)
                        if queue:
                            queue.sort(key=lambda x: len(x['card'][Card.name])) # priorities name-search-matching
                            fixed_setcode: bool = any(x in tweaked_text for x in ['setcode=', 'expansion='])
                            kwgs = dict(slot=slot, amount=amount, fixed_setcode=fixed_setcode)
                            item: DeckItem | None = deck_item(queue[0]['card'], **kwgs)
                            text = tmp_txt
                            break

                [self.prev_searches.update({var: deepcopy(item) if item else None}) for var in (text, org_text,)]

            row_bag[row_num]: DeckItem | None = item

        return row_bag

class ImportExportGroupBTN(GroupBTN):
    def __init__(self, master, **kwargs):
        self.deckbox = master.master.deckbox
        self.deck = master.master.deckbox.deck
        self.buttons: list = master.buttons
        self.buttons.append(self)
        super().__init__(master, **kwargs)
        settings: tuple | None = self.deck.get(self.var, None)
        if settings is not None:
            settings = (settings[0], settings[1], 0,) if len(settings) < 3 else settings
            self.active, self.reversed, self.mode = settings

        self.setText(self.get_text())

    def save_settings(self):
        self.deck[self.var]: tuple = self.active, self.reversed, self.mode,
        self.deckbox.save_deck()

    def mouseReleaseEvent(self, ev):
        super().mouseReleaseEvent(ev)
        self.master.master.show_everything_on_demand()

class CardMarketOut(ImportExportGroupBTN):
    var: str = 'CARDMARKET'

class MoxFieldOut(ImportExportGroupBTN):
    var: str = 'MOXFIELD'

class PlainTextOut(ImportExportGroupBTN):
    var: str = 'PLAIN TEXT'

class ScryfallIDCount(ImportExportGroupBTN):
    var: str = 'JSON OUTPUT'

class ToggleAutoUpdate(ImportExportGroupBTN):
    bg_col: tuple = 100, 15, 15, 255
    var: str = 'REALTIME'

class ToggleIncludeFreeHand(ImportExportGroupBTN):
    var: str = 'READ PLAINTEXT'

class ToggleIncludeDeck(ImportExportGroupBTN):
    var: str = 'READ DECK'

class ToggleOwned(ImportExportGroupBTN):
    bg_col: tuple = 45, 65, 99, 255
    var: str = 'SHOW ONLY OWNED'
    modes: list[str] = ['INCLUDE OWNED', 'EXCLUDE OWNED', 'SHOW ONLY OWNED']
    def only_owned(self) -> bool:
        return 'ONLY' in self.modes[self.mode]

    def exclude_owned(self) -> bool:
        return 'EXCLUDE' in self.modes[self.mode]

    def include_owned(self) -> bool:
        return 'INCLUDE' in self.modes[self.mode]

class ToggleExactSetCode(ImportExportGroupBTN):
    bg_col: tuple = 45, 65, 99, 255
    var: str = 'ANY CARD'
    modes: list[str] = ['ANY CARD', 'EXACT CARD']

    def any_card(self) -> bool:
        return 'ANY' in self.modes[self.mode]

    def exact_card(self) -> bool:
        return 'EXACT' in self.modes[self.mode]


class UpdateDeck(ActiveRevBTN):
    font_size: int = 12
    bg_col: tuple = 45, 65, 99, 255
    tx_col: tuple = 255, 255, 255
    def __init__(self, main, deckbox, importer_exporter, **kwargs):
        self.main = main
        self.deckbox = deckbox
        self.databar = deckbox.databar
        self.deck = deckbox.deck
        self.importer_exporter = importer_exporter
        self.textpout = importer_exporter.textpout
        self.freehand = importer_exporter.freehand
        ss: str = self.textpout.textedit.styleSheet()
        parts: list = ss.split(';')
        for string in parts:
            if string.startswith('color') and ':' in string:
                self.backup_color: str = string.split(':')[-1]
                break
        else:
            self.backup_color: str = ''

        super().__init__(main, adjustable_fontsize=False, **kwargs)
        self.setText('UPDATE DECK')
        self.show()

    def enterEvent(self, event):
        self.draw_background_hover()
        if self.backup_color:
            ss: str = alter_stylesheet(self.textpout.textedit.styleSheet(), key='color', val='rgb(25,225,10)')
            self.textpout.textedit.setStyleSheet(ss)

    def leaveEvent(self, a0):
        self.draw_background_idle()
        if self.backup_color:
            ss: str = alter_stylesheet(self.textpout.textedit.styleSheet(), key='color', val=self.backup_color)
            self.textpout.textedit.setStyleSheet(ss)

    def mouseReleaseEvent(self, ev):
        super().mouseReleaseEvent(ev)
        text: str = self.textpout.textedit.toPlainText()
        row_items: dict[int, DeckItem | None] = self.freehand.rowbag_from_text(text)
        apply_deck: list[DeckItem] = [item for _, item in row_items.items() if item is not None]

        queue: list[dict] = self.deckbox.make_queue_from_deck()
        scry_name: dict[str, str] = {tmp['card'][Card.scryfall_id]: tmp['name'] for tmp in queue}
        name_scry: dict[str, str] = {v: k for k,v in scry_name.items()}
        same_same: bool = len(scry_name) == len(name_scry)

        for item in apply_deck:
            slot: str = item['slot']
            card_data: tuple = item['card_data']
            card_name: str = card_data[Card.name]
            amount: int = item['amount']
            fixed_setcode: bool = item['fixed_setcode']
            if not fixed_setcode and card_name in name_scry and same_same:
                scryfall_id: str = name_scry[card_name]
            else:
                scryfall_id: str = card_data[Card.scryfall_id]

            if slot not in self.deck:
                self.deck[slot]: dict = {scryfall_id: amount}
            elif scryfall_id not in self.deck[slot]:
                self.deck[slot][scryfall_id]: int = amount
            else:
                diff: int = amount - self.deck[slot][scryfall_id]
                if diff:
                    self.deckbox.insert_card_into_deck(scryfall_id, slot, amount=diff)

        self.deckbox.save_deck()

        queue: list[dict] = self.deckbox.make_queue_from_deck()
        self.deckbox.add_queue(queue)
        self.deckbox.reset_queue_size(batch_size=len(queue))
        self.deckbox.draw_next_card()


class ImportExportDataBar(DataBar):
    min_h: int = 28
    def __init__(self, master, **kwargs):
        self.buttons: list = []
        super().__init__(master, **kwargs)

        kwgs = dict(allow_all_off=True, allow_multiple=True, group=[])
        self.include_deck = ToggleIncludeDeck(self, **kwgs, default=True)
        self.include_freehand = ToggleIncludeFreeHand(self, **kwgs, default=True)

        kwgs = dict(allow_all_off=False, group=[])
        self.toggle_owned = ToggleOwned(self, **kwgs, default=True)

        kwgs = dict(allow_all_off=False, group=[])
        self.exact_setcode = ToggleExactSetCode(self, **kwgs, default=True)

        kwgs = dict(allow_all_off=True, group=[])
        self.auto_update = ToggleAutoUpdate(self, **kwgs, default=True)

        kwgs = dict(allow_all_off=False, allow_multiple=False, group=[])
        self.cardmarket_out = CardMarketOut(self, **kwgs)
        self.moxfield_out = MoxFieldOut(self, **kwgs)
        self.plaintext_out = PlainTextOut(self, **kwgs, default=True)
        self.scryfallid_count = ScryfallIDCount(self, **kwgs)

        [btn.show() for btn in self.buttons]
        groups: list = []
        for btn in self.buttons:
            if btn.group not in groups:
                groups.append(btn.group)

        for btns in groups:
            if all(self.master.deck.get(btn.var, None) is None for btn in btns):
                [btn.toggle_btn() for btn in btns if btn.default]

    def resizeEvent(self, a0):
        h: int = self.height()
        w: int = self.width()
        self.background.resize(w, h)
        self.draw_background_idle()

    def expand(self):
        tw_extra: int = 10
        mid_extra: int = 120
        shift: int = 6

        lft: int = 4
        for btn in [btn for btn in self.buttons if btn.group == self.include_freehand.group]:
            text: str = btn.get_longest_text()
            tw: int = btn.textlabel.get_text_width(text) + tw_extra
            btn.setGeometry(lft, 4, tw, self.min_h - 8)
            lft += tw

        lft += shift
        for btn in [btn for btn in self.buttons if btn.group in (self.toggle_owned.group, self.exact_setcode.group,)]:
            text: str = btn.get_longest_text()
            tw: int = btn.textlabel.get_text_width(text) + tw_extra
            btn.setGeometry(lft, 4, tw, self.min_h - 8)
            lft += tw

        lft += mid_extra
        for btn in [btn for btn in self.buttons if btn.group == self.cardmarket_out.group]:
            text: str = btn.get_longest_text()
            tw: int = btn.textlabel.get_text_width(text) + tw_extra
            btn.setGeometry(lft, 4, tw, self.min_h - 8)
            lft += tw

        lft += shift
        text: str = self.auto_update.get_longest_text()
        tw: int = self.auto_update.textlabel.get_text_width(text) + tw_extra
        self.auto_update.setGeometry(lft, 4, tw, self.min_h - 8)
        lft += tw

        self.resize(lft + 4, self.min_h)


class ImportExport(MoveLabel):
    var: str = 'import_export_geo'
    def __init__(self, main, deckbox, **kwargs):
        self.main = main
        self.deckbox = deckbox
        self.deck = deckbox.deck
        self.prev_searches: dict = {}
        super().__init__(main, **kwargs)
        self.databar = ImportExportDataBar(self)
        self.freehand = FreeHand(self)
        self.textpout = TextPOut(self)

        self.databar.expand()
        w, h = self.databar.width(), self.databar.min_h + self.freehand.min_h,

        top: int = self.databar.geometry().bottom() + 1
        cnt: int = self.databar.width() // 2
        self.freehand.setGeometry(0, top, cnt, h - top)
        self.textpout.setGeometry(cnt, top, w - cnt, h - top)

        self.updatedeck_btn = UpdateDeck(self.main, self.deckbox, importer_exporter=self)

        self.resize(w, h)

        xy: tuple | None = self.get_saved_coords()
        self.move(*xy or (50, 50))

    def closeEvent(self, *args):
        try:
            self.updatedeck_btn.close()
        except (AttributeError,RuntimeError):
            ...
        super().closeEvent(*args)

    def get_saved_coords(self) -> tuple | None:
        try:
            lft, top = self.deck[self.var][:2]
        except (TypeError, KeyError):
            ...
        else:
            lft = min(self.main.width() - 50, lft)
            top = min(self.main.height() - 50, top)
            return max(50, lft), max(0, top)

    def mouseReleaseEvent(self, ev):
        super().mouseReleaseEvent(ev)
        self.save_coords()
        self.updatedeck_btn.raise_()

    def moveEvent(self, *args):
        super().moveEvent(*args)
        lft: int = self.updatedeck_btn.width()
        top: int = self.geometry().bottom() + 1
        self.updatedeck_btn.move(self.geometry().right() - lft, top)
        self.updatedeck_btn.raise_()

    def save_coords(self):
        geo = self.geometry()
        self.deck[self.var]: tuple = geo.left(), geo.top(), geo.right(), geo.bottom()
        self.deckbox.save_deck()

    def resizeEvent(self, a0):
        w, h = self.width(), self.height()
        self.databar.resize(w, self.databar.min_h)
        tw: int = self.updatedeck_btn.get_text_width() + 10
        th: int = self.updatedeck_btn.get_text_height() + 4
        lft: int = self.geometry().right() - tw
        top: int = self.geometry().bottom() + 1

        self.updatedeck_btn.setGeometry(lft, top, tw, th)

    def auto_update(self) -> bool:
        return any(btn.active for btn in self.databar.buttons if isinstance(btn, ToggleAutoUpdate))

    def read_userinput(self) -> bool:
        return any(btn.active for btn in self.databar.buttons if isinstance(btn, ToggleIncludeFreeHand))

    def hide_owned(self) -> bool:
        return any(btn.exclude_owned() for btn in self.databar.buttons if isinstance(btn, ToggleOwned))

    def show_only_owned(self) -> bool:
        return any(btn.only_owned() for btn in self.databar.buttons if isinstance(btn, ToggleOwned))

    def include_deck(self) -> bool:
        return any(btn.active for btn in self.databar.buttons if isinstance(btn, ToggleIncludeDeck))

    def export_deck(self):
        if self.auto_update():
            self.show_everything_on_demand()

    def exact_card(self) -> bool:
        return any(btn.exact_card() for btn in self.databar.buttons if isinstance(btn, ToggleExactSetCode))

    def row_items_from_freehand(self) -> dict[int, DeckItem | None]:
        row_item: dict[int, DeckItem | None] = self.freehand.get_rowbag()
        return row_item

    def items_from_deck(self) -> list[DeckItem | None]:
        if len(self.prev_searches) > 5000:
            self.prev_searches = {}

        tmp_items: list = []
        for slot in self.deckbox.deckslots:
            for scry, amount in self.deck.get(slot, {}).items():
                tmp_items.append(dict(scryfall_id=scry, amount=amount, slot=slot))

        missing: set[str] = {x['scryfall_id'] for x in tmp_items if x['scryfall_id'] not in self.prev_searches}
        if missing:
            marks: str = ','.join(['?'] * len(missing))
            q: str = f'select * from cards where scryfall_id in ({marks}) and (side is "a" or side is null)'
            v: list[str] = list(missing)
            [self.prev_searches.update({d[Card.scryfall_id]: d}) for d in MTGData.cursor.execute(q, v).fetchall()]

        deck: list[DeckItem | None] = []
        for item in tmp_items:
            scry: str = item['scryfall_id']
            if scry not in self.prev_searches:
                continue

            card_data: tuple = self.prev_searches[scry]
            tmp = deck_item(card_data, amount=item['amount'], slot=item['slot'], fixed_setcode=True)
            deck.append(tmp)

        return deck

    def set_owned_flag(self, items_out: list[DeckItem | None]):
        only_owned: bool = self.show_only_owned()
        hide_owned: bool = self.hide_owned()
        if not only_owned and not hide_owned:
            return

        exact_card: bool = self.exact_card()
        for n, item in enumerate(items_out):
            if item is None:
                continue

            card_data: tuple = item['card_data']
            own_card: bool = card_owned(card_data)
            if exact_card:
                item['own_card'] = own_card
                item['own_name'] = own_card and name_owned(card_data)
            else:
                item['own_card'] = own_card
                item['own_name'] = own_card or name_owned(card_data)

    def null_unwanted_cards(self, items_out: list[DeckItem | None]):
        only_owned: bool = self.show_only_owned()
        hide_owned: bool = self.hide_owned()
        exact_card: bool = self.exact_card()
        for n, item in enumerate(items_out):
            if item is None:
                continue

            own_card: bool = item['own_card']
            own_name: bool = item['own_name']
            if only_owned:
                if exact_card and not own_card:
                    items_out[n] = None
                elif not exact_card and not own_name:
                    items_out[n] = None

            elif hide_owned:
                if exact_card and own_card:
                    items_out[n] = None
                elif not exact_card and own_name:
                    items_out[n] = None

    def change_name_only_card(self, items_out: list[DeckItem | None]):
        if not self.show_only_owned() or self.exact_card():
            return

        names: set[str] = set()
        for item in items_out:
            if item is None:
                continue

            if not item['own_card'] and item['own_name']:
                card_name: str = item['card_name']
                names.add(card_name)

        if names:
            name_marks: str = ','.join(['?'] * len(names))
            scry_marks: str = ','.join(['?'] * len(Owned.scryfall_ids))
            q: str = f'select * from cards where name in ({name_marks}) and scryfall_id in ({scry_marks})'
            v: tuple = tuple(names) + tuple(Owned.scryfall_ids)
            name_carddata: dict[str, tuple] = {x[Card.name]: x for x in MTGData.cursor.execute(q, v).fetchall()}

            for item in items_out:
                if item is None:
                    continue

                card_name: str = item['card_name']
                if not item['own_card'] and item['own_name'] and card_name in name_carddata:
                    item['card_data'] = name_carddata[card_name]

    def show_everything_on_demand(self):
        user_input: bool = self.read_userinput()
        include_deck: bool = self.include_deck()

        btns: list = [x for x in self.databar.buttons if x.group == self.databar.cardmarket_out.group]
        active_btn = next(iter([x for x in btns if x.active] or [self.databar.plaintext_out]))

        items_out: list[DeckItem | None] = []
        user_inputs: list[DeckItem | None] = []

        if user_input:
            user_inputs += [item for _, item in self.row_items_from_freehand().items()]
            items_out += user_inputs

        if include_deck:
            deck: list[DeckItem] = self.items_from_deck()
            deck.sort(key=lambda x: x['card_data'][Card.name])
            deck.sort(key=lambda x: x['slot'])
            items_out += [None] if (user_inputs and deck) else [] # add space between user_inputs and the actual deck
            items_out += deck

        self.set_owned_flag(items_out)
        self.null_unwanted_cards(items_out)
        self.change_name_only_card(items_out)

        if isinstance(active_btn, MoxFieldOut):
            text: str = self.moxfield_output_string(deck=items_out, ignore_slots=True, show_empty=not not user_inputs)

        elif isinstance(active_btn, CardMarketOut):
            text: str = self.cardmarket_output_string(deck=items_out, ignore_slots=True, show_empty=not not user_inputs)

        elif isinstance(active_btn, ScryfallIDCount):
            json_output: dict = {}
            for item in items_out:
                if item is None:
                    continue
                    
                slot: str = item['slot']
                scry: str = item['card_data'][Card.scryfall_id]
                amount: int = item['amount']
                if slot not in json_output:
                    json_output[slot]: dict = {}

                json_output[slot][scry]: int = amount

            text: str = json.dumps(json_output)
        else:
            text: str = self.plaintext_output_string(deck=items_out, ignore_slots=True, show_empty=not not user_inputs)

        self.textpout.textedit.setPlainText(text)

    def plaintext_output_string(self, deck: list[DeckItem | None], ignore_slots: bool = False, show_empty: bool = True) -> str:
        outs: list[str] = []
        prev: str = '[:::NOPE:::]'
        for bag in deck:
            if bag is None:
                outs.append('') if show_empty else ...
            else:
                amount: int = bag['amount']
                cardname: str = bag['card_name']
                if not ignore_slots:
                    slot: str = bag['slot']
                    if slot not in prev:
                        outs += ['', slot.upper() + ':']
                        prev = slot

                outs.append(f'{amount} {cardname}')
        return '\n'.join(outs)

    def moxfield_output_string(self, deck: list[DeckItem | None], ignore_slots: bool = False, show_empty: bool = True) -> str:
        outs: list[str] = []
        prev: str = '[:::NOPE:::]'
        for bag in deck:
            if bag is None:
                outs.append('') if show_empty else ...
            else:
                card_data: tuple = bag["card_data"]
                amount: int = bag['amount']
                cardname: str = bag['card_name']
                if not ignore_slots:
                    slot: str = bag['slot']
                    if slot not in prev:
                        outs += ['', slot.upper() + ':']
                        prev = slot

                setcode: str = card_data[Card.setcode]
                num: str = card_data[Card.number] or ''

                while ' // ' in cardname:
                    args: tuple = ' // ', ' / '
                    cardname = cardname.replace(*args)

                outs.append(f'{amount} {cardname} ({setcode}) {num}')

        return '\n'.join(outs)

    def cardmarket_output_string(self, deck: list[DeckItem | None], ignore_slots: bool = False, show_empty: bool = True) -> str:
        outs: list[str] = []
        prev: str = '[:::NOPE:::]'
        for bag in deck:
            if bag is None:
                outs.append('') if show_empty else ...
            else:
                card_data: tuple = bag["card_data"]
                amount: int = bag['amount']
                cardname: str = bag['card_name']
                if not ignore_slots:
                    slot: str = bag['slot']
                    if slot not in prev:
                        outs += ['', slot.upper() + ':']
                        prev = slot

                single_sided: bool = card_data[Card.layout] not in ['transform', 'modal_dfc', 'meld']
                if single_sided and ' /' in cardname:
                    cardname = cardname[:cardname.find(' /')]

                setcode: str = card_data[Card.setcode]
                setname: str | None = MTGData.SETCODE_EXPNAME.get(setcode, None)
                outs.append(f'{amount}x {cardname} ({setname or setcode})')

        return '\n'.join(outs)

class ImportExportBTN(ActiveRevBTN):
    var: str = 'IMPORT / EXPORT'
    def mouseReleaseEvent(self, ev):
        self.open_close()

    def open_close(self):
        self.active = not self.active
        showbox = self.master.master
        showbox.deck[self.var]: bool = self.active
        showbox.save_deck()

        if showbox.importer_exporter is not None:
            try:
                showbox.importer_exporter.close()
            finally:
                showbox.importer_exporter = None
        else:
            showbox.importer_exporter = ImportExport(showbox.main, deckbox=showbox)
            showbox.importer_exporter.export_deck()
            showbox.importer_exporter.show()

        if showbox.importer_exporter is not None:
            self.draw_background_hover()
