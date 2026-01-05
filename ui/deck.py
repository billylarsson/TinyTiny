from PIL                  import Image
from PIL.ImageDraw        import ImageDraw
from PIL.ImageQt          import ImageQt
from PyQt6                import QtCore, QtGui, QtWidgets
from copy                 import deepcopy
from cardgeo.cardgeo import CardGeo
from ui.basics            import Label
from ui.commander         import Commander
from ui.databar           import CardResizer, DataBar, QueueStatus, Sorters
from ui.deckdetails       import DeckDetails, DeckDetailsBTN
from ui.import_and_export import ImportExport, ImportExportBTN
from ui.showbox           import ShowBox
from ui.showcase          import ShowCase
from useful.database      import Card, MTGData, Set
from useful.tech          import add, add_rgb, add_rgba, shrinking_rect, sub
import time


def empty_deck(uuid: float | None = None) -> dict:
    uuid: float = uuid or time.time()  # I know, I know...
    new_deck: dict = dict(
        name='NEW DECKBOX',
        uuid=uuid,
        maindeck={},
        sideboard={},
        commander={},
        companion={},
    )
    return new_deck

def deckslots() -> set[str]:
    return {slot for slot, bag in empty_deck(0.0).items() if isinstance(bag, dict)}

class DeckQueueStatus(QueueStatus):
    def update_status(self):
        queue: list = self.master.master.cards
        showcases: list = [card['showcase'] for card in queue if card['showcase']]
        amounts: int = sum(showcase.get_amount() for showcase in showcases) if showcases else 0
        self.textlabel.setText(f'DECKSIZE {amounts}')
        text_w: int = self.textlabel.get_text_width() + 20
        self.resize(max(text_w, self.min_w), self.height())

class DeckCardResizer(CardResizer):
    def __init__(self, master, **kwargs):
        self.deckbox = master.master
        geo_data: dict | None = self.deckbox.deck.get(self.settings_var, None)
        super().__init__(master, geo_data=geo_data, **kwargs)

    def save_geo_data(self):
        geo_data: dict = self.card_geo.get_data()
        self.deckbox.deck[self.settings_var]: dict = geo_data
        self.deckbox.save_deck()

class DeckDataBar(DataBar):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.sorters = Sorters(self)
        self.deck_details = DeckDetailsBTN(self)
        self.import_export = ImportExportBTN(self)
        self.card_resizer = DeckCardResizer(self)


class AmountLabel(Label):
    def __init__(self, master, **kwargs):
        self.showcase = master
        self.deckbox = self.showcase.deckbox
        self.deck: dict = self.deckbox.deck
        super().__init__(master, **kwargs)
        self.background = Label(self)
        self.textlabel = Label(self)
        self.textlabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.textlabel.setContentsMargins(10,0,0,0)
        self.textlabel.setStyleSheet('color:rgb(180,180,180);font:11px')

    def mouseReleaseEvent(self, ev):
        if ev.button().value == 1:
            self.increase_amount()

        elif ev.button().value == 2:
            self.decrease_amount()

    def increase_amount(self, amount: int = 1):
        self.showcase.amount += amount
        self.update_deck_and_showcase()

    def decrease_amount(self, amount: int = 1):
        self.showcase.amount -= amount
        self.update_deck_and_showcase()

    def update_deck_and_showcase(self):
        self.showcase.update_visuals_and_save()

    def resizeEvent(self, a0):
        [label.resize(self.width(), self.height()) for label in (self.background, self.textlabel)]
        args: tuple = 'RGBA', (self.background.width(), self.background.height()), (0, 0, 0, 0)
        im = Image.new(*args)
        draw = ImageDraw(im)

        x1, y1, x2, y2 = 0, 0, im.width - 1, im.height - 1
        r, g, b, a = 30, 30, 30, 255
        for x in range(im.width):
            draw.line((x, 0, x, y2), fill=(r, g, b, a))
            draw.point((x, y2), fill=(155,155,155,a))
            a = sub(a, min_sub=1)

        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)

    def show_amount(self):
        self.textlabel.setText(str(self.showcase.get_amount()))

class DeckShowCase(ShowCase):
    def __init__(self, move_canvas, amount: int, slot: str, **kwargs):
        self.slot: str = slot
        self.amount: int = amount
        self.deckbox = move_canvas.master.master.master
        self.deck: dict = self.deckbox.deck
        super().__init__(move_canvas, **kwargs)
        self.amount_label = AmountLabel(self)

    def update_visuals_and_save(self):
        scryfall_id: str = self.card_data[Card.scryfall_id]
        if self.slot not in self.deck:
            self.deck[self.slot] = {}

        self.set_correct_amount()
        self.deck[self.slot][scryfall_id] = self.get_amount()
        self.amount_label.show_amount()

        if self.get_amount() < 0:
            self.remove_from_deck_and_queue()
            self.close()
            if self.slot in 'commander':
                self.deckbox.commander.show_commander()

        self.deckbox.save_deck()

        if self.deckbox.databar.queue_status:
            self.deckbox.databar.queue_status.update_status()

        if self.deckbox.deckdetails:
            self.deckbox.deckdetails.update_fidgets()

        if self.deckbox.importer_exporter:
            self.deckbox.importer_exporter.export_deck()

    def set_correct_amount(self):
        if any(x not in self.card_data[Card.type].split() for x in ['Basic', 'Land']):
            if self.deckbox.is_commander:
                self.amount = min(1, self.get_amount())
            else:
                self.amount = min(4, self.get_amount())

    def enterEvent(self, *args):
        super().enterEvent(*args)
        self.fidget_draw_background_hover()

    def fidget_draw_background_hover(self):
        if self.master.showbox.deckdetails:
            for _, rolldown in self.master.showbox.deckdetails.types.items():
                for _, fidget in rolldown.fidgets.items():
                    if self in fidget.showcases:
                        fidget.draw_background_hover()

    def leaveEvent(self, *args):
        super().leaveEvent(*args)
        self.fidget_draw_background_idle()

    def fidget_draw_background_idle(self):
        if self.master.showbox.deckdetails:
            for _, rolldown in self.master.showbox.deckdetails.types.items():
                for _, fidget in rolldown.fidgets.items():
                    if self in fidget.showcases:
                        fidget.draw_background_idle()

    def mouseReleaseEvent(self, ev):
        pre_scryfall_id: str = self.card_data[Card.scryfall_id]
        super().mouseReleaseEvent(ev)
        now_scryfall_id: str = self.card_data[Card.scryfall_id]

        if now_scryfall_id != pre_scryfall_id:
            try:
                self.deck[self.slot].pop(pre_scryfall_id)
            except KeyError:
                if self.slot not in self.deck:
                    self.deck[self.slot]: dict = {}
            finally:
                if now_scryfall_id in self.deck[self.slot]:
                    self.deck[self.slot][now_scryfall_id] += self.get_amount()
                else:
                    self.deck[self.slot][now_scryfall_id] = self.get_amount()

            self.update_visuals_and_save()

    def remove_from_deck_and_queue(self):
        scry_id: str = self.card_data[Card.scryfall_id]
        try:
            self.deck[self.slot].pop(scry_id)
        except KeyError:
            ...

        for box in self.deckbox.cards:
            if box['showcase'] == self:
                self.deckbox.cards.remove(box)
                break

    def move_to_slot(self, slot: str):
        scry_id: str = self.card_data[Card.scryfall_id]
        amount: int = self.get_amount()

        for box in self.deckbox.cards:
            if box['scryfall_id'] in scry_id and box['slot'] in self.slot:
                box['slot'] = slot
                break
        try:
            self.deck[self.slot].pop(scry_id)
        except KeyError:
            ...

        self.slot = slot
        self.deck[slot] = self.deck[slot] if slot in self.deck else {}

        if scry_id not in self.deck[slot]:
            self.deck[slot][scry_id] = amount
        else:
            self.deck[slot][scry_id] += amount

        self.deckbox.save_deck()
        self.fidget_draw_background_idle()

    def get_amount(self) -> int:
        return self.amount

    def resizeEvent(self, *args):
        super().resizeEvent(*args)
        self.amount_label.setGeometry(3, 3, self.width(), self.height() // 20)
        self.amount_label.show_amount()



class Deck(ShowBox):
    settings_var: str = 'DeckBox!'

    # looks good to have the startingbox filled with perhaps 4 cards per row before manually resizing
    cardgeo: dict = CardGeo().get_data()
    single: int = cardgeo['offset'] + cardgeo['w']
    w: int = (single * 4) + cardgeo['offset']
    min_w: int = max(ShowBox.min_w, w + 10)

    is_commander: bool = True
    deckdetails: DeckDetails | None = None
    importer_exporter: ImportExport | None = None
    def __init__(self, master, uuid: float, **kwargs):
        self.deckslots: set[str] = deckslots()
        self.settings_var = f'DeckBox: {uuid}'
        self.main = master
        deckboxes: dict = self.main.load_setting('deckboxes') or {}
        self.deck: dict = deepcopy(deckboxes.get(uuid, empty_deck()))
        super().__init__(master, **kwargs)
        self.databar = DeckDataBar(self)
        self.commander = Commander(self.main, deckbox=self)
        self.attached_objects.append(self.commander)
        self.commander.show()

        if self.deck.get(DeckDetailsBTN.var, True):
            self.databar.deck_details.open_close()
            self.databar.deck_details.draw_background_idle()

        if self.deck.get(ImportExportBTN.var, True):
            self.databar.import_export.open_close()
            self.databar.import_export.draw_background_idle()



    def closeEvent(self, *args):
        for obj in [self.deckdetails, self.importer_exporter]:
            if obj is not None:
                try:
                    obj.close()
                except (AttributeError,RuntimeError):
                    ...

        super().closeEvent(*args)

    def raise_attached_objects(self):
        super().raise_attached_objects()
        self.raise_time = time.time()

    def enterEvent(self, *args):
        super().enterEvent(*args)
        uuid: float = self.deck.get('uuid', 1.0)
        for deckbox in self.main.deckboxes.deckboxes:
            if uuid == deckbox.deckbox.get('uuid', 2.0):
                deckbox.draw_canvas_on()
                deckbox.open_btn.draw_canvas_on()
                deckbox.del_btn.draw_canvas_on()
                break

    def leaveEvent(self, *args):
        super().leaveEvent(*args)
        uuid: float = self.deck.get('uuid', 1.0)
        for deckbox in self.main.deckboxes.deckboxes:
            if uuid == deckbox.deckbox.get('uuid', 2.0):
                deckbox.draw_canvas_off()
                deckbox.open_btn.draw_canvas_off()
                deckbox.del_btn.draw_canvas_off()
                break

    def save_deck(self):
        uuid: float = self.deck.get('uuid', time.time())
        deckboxes: dict = self.main.load_setting('deckboxes') or {}
        if deckboxes.get(uuid, None) != self.deck:
            deckboxes[uuid]: dict = deepcopy(self.deck)
            self.main.save_setting('deckboxes', deckboxes)

    def new_showcase(self, box: dict) -> ShowCase:
        kwgs = dict(card_data=box['card'], bag=box['bag'], amount=box['amount'], slot=box['slot'])
        return DeckShowCase(self.move_canvas, **kwgs)

    def insert_card_into_box(self, *args, **kwargs):
        self.insert_card_into_deck(*args, **kwargs)

    def deck_stability(self, card_data: tuple, slot: str):
        showcases: list[DeckShowCase] = [x['showcase'] for x in self.cards if x['showcase']]
        if slot in 'commander':
            for showcase in showcases:
                if showcase.card_data == card_data and showcase.slot not in slot:
                    showcase.move_to_slot(slot)
                    self.commander.show_commander()

                elif showcase.card_data != card_data and showcase.slot in slot:
                    showcase.move_to_slot('maindeck')
                    self.commander.show_commander()
        else:
            for showcase in showcases:
                if showcase.card_data == card_data and showcase.slot in 'commander':
                    showcase.move_to_slot(slot)
                    self.commander.show_commander()

    def insert_card_into_deck(self, scryfall_id: str, slot: str = 'maindeck', amount: int = 1):
        q: str = 'select * from cards where scryfall_id is (?) and (side is "a" or side is null)'
        v: tuple = scryfall_id,
        card_data: tuple | None = MTGData.cursor.execute(q, v).fetchone()
        if not card_data:
            return

        self.deck_stability(card_data, slot)
        showcases: list[DeckShowCase] = [x['showcase'] for x in self.cards if x['showcase']]
        for showcase in showcases:
            if slot in showcase.slot and scryfall_id in showcase.card_data[Card.scryfall_id]:
                mc = self.scroller.move_canvas
                sc = self.scroller.scope_canvas

                want_y: int = (sc.height() // 2) - (showcase.height() // 2)
                target_y: int = want_y - showcase.geometry().top()

                mc.move(mc.geometry().left(), min(0, target_y))

                showcase.amount_label.increase_amount(amount)
                break
        else:
            if slot not in self.deck:
                self.deck[slot]: dict = {scryfall_id: amount}
            elif scryfall_id not in self.deck[slot]:
                self.deck[slot][scryfall_id]: int = amount
            else:
                self.deck[slot][scryfall_id] += amount

            queue: list[dict] = self.make_queue_from_deck()
            queue = [obj for obj in queue if obj['slot'] in slot and obj['scryfall_id'] in scryfall_id]
            self.add_queue(queue)

            self.draw_next_card(scryfall_id)
            self.save_deck()

            xy: tuple = self.scroller.geometry().left(), self.scroller.get_max_y()
            self.scroller.move(*xy)
            self.scroller.cards_follows_scroller()

        if slot in 'commander':
            self.commander.show_commander()

    def make_queue_from_deck(self) -> list[dict]:
        queue: list[dict] = []
        scry_ids: set[str] = set()
        for slot in {slot for slot in self.deckslots if slot in self.deck}:
            for scryfall_id, amount in self.deck[slot].items():
                box: dict = dict(
                    scryfall_id=scryfall_id, amount=amount, name=None, card=None, bag=None, showcase=None, slot=slot,
                )
                scry_ids.add(scryfall_id)
                queue.append(box)

        marks: list = ['?'] * len(scry_ids)
        q: str = f'select * from cards where scryfall_id in ({",".join(marks)}) and (side is "a" or side is null)'
        cards: list = MTGData.cursor.execute(q, list(scry_ids)).fetchall()
        for n in range(len(queue) - 1, -1, -1):
            box: dict = queue[n]
            for card in cards:
                if card[Card.scryfall_id] == box['scryfall_id']:
                    name: str = card[Card.name]
                    box['card'] = card
                    box['name'] = name
                    box['bag'] = MTGData.NAME_BAG[name]

        return [box for box in queue if box['card'] and box['bag']]

    def draw_next_card(self, *args, **kwargs):
        super().draw_next_card(*args, **kwargs)
        if self.deckdetails:
            self.deckdetails.update_fidgets()

        if self.importer_exporter:
            self.importer_exporter.export_deck()

    def redraw_deck(self):
        queue: list[dict] = self.make_queue_from_deck()
        if queue:
            self.clear_queue()
            self.clear_canvas()
            self.add_queue(queue)
            self.sort_cards()
            self.reset_queue_size(batch_size=len(queue))
            self.draw_next_card()

