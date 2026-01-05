import sqlite3,os,time

class Card:
    artist: int
    cmc: int
    color_identity: int
    colors: int
    frame_effects: int
    keywords: int
    layout: int
    mana_cost: int
    name: int
    number: int
    power: int
    rarity: int
    scryfall_id: int
    setcode: int
    side: int
    text: int
    toughness: int
    type: int
    types: int

class Set:
    """"""

class Bag:
    def __init__(self):
        self.cards: list[tuple] = []
        self.processing: list[tuple] = []
        self.prefered: tuple | None = None
        self.is_stupid: bool = True
        self.legal: dict = {}

def database_integrity(database_path: str):
    if not os.path.exists(database_path) or not os.path.getsize(database_path):
        from useful.update_database import fresh_databases
        if os.path.exists(fresh_databases):
            import zipfile
            with zipfile.ZipFile(fresh_databases, mode='r') as zf:
                for fname in zf.namelist():
                    if database_path.endswith(fname):
                        zf.extract(fname, database_path[:len(database_path) - len(fname)])

class MTGData:
    from useful.update_database import legal_card_datas, db_path_card_datas, make_quick_db, make_quick_legal_db
    database_integrity(db_path_card_datas)
    database_integrity(legal_card_datas)

    names: list[str] = __file__.split(os.sep)
    subdir: str = os.sep.join(x for x in names[:-2])

    if not os.path.exists(db_path_card_datas):
        make_quick_db()

    if not os.path.exists(legal_card_datas):
        make_quick_legal_db()

    print(f'initializing database, ', end='', flush=True)
    create_start: float = time.time()

    @staticmethod
    def sort_namebag(NAME_BAG: dict, SETCODE_TIME: dict, setcode_type: dict):
        for name, bag in NAME_BAG.items():
            bag.cards.sort(key=lambda x: SETCODE_TIME[x[Card.setcode]], reverse=True)
            for card in bag.cards:
                if setcode_type[card[Card.setcode]] in ['expansion', 'core']:
                    prefered_setcode: str = card[Card.setcode]
                    bag.is_stupid = False
                    break
            else:
                for card in bag.cards:
                    if setcode_type[card[Card.setcode]] in ['draft_innovation', 'masters'] and len(
                            card[Card.setcode]) == 3:
                        prefered_setcode: str = card[Card.setcode]
                        break
                else:
                    for card in bag.cards:
                        if len(card[Card.setcode]) == 3:
                            prefered_setcode: str = card[Card.setcode]
                            break
                    else:
                        prefered_setcode: str = bag.cards[0][Card.setcode]

            cards: list[tuple] = [x for x in bag.cards if x[Card.setcode] == prefered_setcode]
            if len(cards) == 1:
                bag.prefered = cards[0]
            else:
                card_val: list[tuple] = [(card, (card[Card.frame_effects] or '').count(',')) for card in cards]
                card_val.sort(key=lambda x: x[1])
                card_val = [x for x in card_val if x[1] == card_val[0][1]]
                if len(card_val) > 1:
                    dual: list[tuple] = []
                    for card, _ in card_val:
                        digs: str = ''.join([x for x in (card[Card.number] or '') if x.isdigit()] or ['-1'])
                        dual.append((card, int(digs)))
                    dual.sort(key=lambda x: x[1])
                    bag.prefered = dual[0][0]
                else:
                    bag.prefered = card_val[0][0]

    connection = sqlite3.connect(db_path_card_datas)
    cursor = connection.cursor()

    q: str = 'PRAGMA table_info(cards)'
    [setattr(Card, col_name, col_num) for col_num, col_name, *_ in cursor.execute(q).fetchall()]

    q: str = 'PRAGMA table_info(sets)'
    [setattr(Set, col_name, col_num) for col_num, col_name, *_ in cursor.execute(q).fetchall()]


    q: str = (f'select setcode, releasedate_epoch from sets '
              f'where setcode is not null '
              f'and releasedate_epoch is not null '
              f'and type is not null')

    SETCODE_TIME: dict[str, int] = {setcode: release_epoch for setcode, release_epoch in cursor.execute(q).fetchall()}
    SETCODES: set[str] = set()
    for setcode in SETCODE_TIME:
        SETCODES.add(setcode)

    q: str = 'select * from cards where (side is "a" or side is null)'
    all_cards: list[tuple] = cursor.execute(q).fetchall()
    NAME_BAG: dict[str, Bag] = {}
    for card in all_cards:
        cardname: str = card[Card.name]
        setcode: str = card[Card.setcode]
        if setcode in SETCODES:
            if cardname not in NAME_BAG:
                NAME_BAG[cardname] = Bag()
            NAME_BAG[cardname].cards.append(card)

    placehldrs: str = ','.join(['?'] * len(SETCODES))
    q: str = f'select setcode, type from sets where setcode in ({placehldrs})'
    setcode_type: dict = {setcode: exptype for setcode, exptype in cursor.execute(q, list(SETCODES)).fetchall()}

    q: str = f'select setcode, name from sets where setcode in ({placehldrs})'
    SETCODE_EXPNAME: dict = {setcode: expname for setcode, expname in cursor.execute(q, list(SETCODES)).fetchall()}
    EXPNAME_SETCODE: dict = {expname: setcode for setcode, expname in SETCODE_EXPNAME.items()}

    sort_start: float = time.time()
    sort_namebag(NAME_BAG, SETCODE_TIME, setcode_type)
    sort_end: float = time.time() - sort_start

    create_end: float = time.time() - create_start
    print(f'\33[33:1:15m{len(NAME_BAG)}\33[0m cards loaded into ram in {round(create_end, 2)} seconds (\33[38:5:249msorting {round(sort_end, 2)}\33[0m)', flush=True)

    @staticmethod
    def insert_legalities():
        from useful.update_database import legal_card_datas
        print(f'beginning legalities insertion, ', end='', flush=True)
        timer_start: float = time.time()
        q: str = 'select name, csv_status from legalities'
        legal_connection = sqlite3.connect(legal_card_datas)
        legal_cursor = legal_connection.cursor()
        name_csv: dict = {name: csv for name, csv in legal_cursor.execute(q).fetchall()}
        legal_cursor.close()
        legal_connection.close()

        for name, bag in MTGData.NAME_BAG.items():
            bag.legal = dict(legal=set(), banned=set(), restricted=set())
            if name in name_csv:
                parts: list = name_csv[name].lower().split(',')
                for part in parts:
                    fmt, status = part.split(':')
                    if status in ['legal']:
                        bag.legal['legal'].add(fmt)
                    elif status in ['restricted']:
                        bag.legal['restricted'].add(fmt)
                    elif status in ['banned']:
                        bag.legal['banned'].add(fmt)


        timer_end: float = time.time() - timer_start
        print(f'legal statuses for \33[33:1:15m{len(name_csv)}\33[0m different cards inserted in {round(timer_end, 2)} seconds', flush=True)


class Owned:
    scryfall_ids: set[str] = set()
    all_names: set[str] = set()
    textfile_updated: bool = False
    textfile_imported: bool = False
    names_imported: bool = False
    subdir: str = os.sep.join(__file__.split(os.sep)[:-2])
    path: str = f'{subdir}{os.sep}scryfall_ids.csv'

    def import_textfile(self):
        if not self.textfile_imported:
            if os.path.exists(self.path):
                with open(self.path) as f:
                    cont = f.read()
                    parts: list[str] = cont.strip(',\n\t ').split(',')
                    [self.scryfall_ids.add(x) for x in parts]

            Owned.textfile_imported = True

    def import_names(self):
        if not self.names_imported:
            self.import_textfile()
            if self.scryfall_ids:
                scry_ids: list[str] = list(Owned.scryfall_ids)
                marks: str = ','.join(['?'] * len(scry_ids))
                q: str = f'select * from cards where scryfall_id in ({marks}) and (side is "a" or side is null)'
                [self.all_names.add(card[Card.name]) for card in MTGData.cursor.execute(q, scry_ids).fetchall()]

            Owned.names_imported = True

    def update_ownedfile_from_plmtg(self):
        if not self.textfile_updated:
            path: str = '/home/plutonergy/Coding/PLMTG_v4/orders.sqlite'
            if not os.path.exists(path):
                print(f'{path} doesnt exists!')
                return

            con = sqlite3.connect(path)
            cur = con.cursor()

            q: str = 'select uuid from "order" where foil is (?)'
            v: tuple = True,
            arrived_uuids: set[str] = set(x[0] for x in cur.execute(q, v).fetchall())

            cur.close()
            con.close()

            if not arrived_uuids:
                print(f'couldnt find any arrived uuids')
                return

            path = '/home/plutonergy/Coding/PLMTG_v4/AllPrintings.sqlite'
            if not os.path.exists(path):
                print(f'{path} doesnt exists!')
                return

            self.import_textfile()

            con = sqlite3.connect(path)
            cur = con.cursor()

            q: str = f'select scryfall_id from cards where uuid in ({",".join(["?"] * len(arrived_uuids))})'
            arrived_scryfall_ids: set[str] = {x[0] for x in cur.execute(q, tuple(arrived_uuids)).fetchall()}

            cur.close()
            con.close()

            new_scrys: set[str] = {x for x in arrived_scryfall_ids if x not in self.scryfall_ids}
            if not new_scrys:
                print(f'no update needed, couldnt find any new arrived cards')
                return
            else:
                marks: str = ','.join(['?'] * len(new_scrys))
                q: str = f'select * from cards where scryfall_id in ({marks}) and (side is "a" or side is null)'
                new_cards: list[tuple] = MTGData.cursor.execute(q, list(new_scrys)).fetchall()
                if new_cards:
                    new_cards.sort(key=lambda x: x[Card.name])
                    for n, card in enumerate(new_cards):
                        lenght: int = len(new_cards) + 1
                        strnum: str = f'{n + 1}'
                        while len(strnum) < lenght:
                            strnum = f'0{strnum}'

                        print(f'\33[38:5:249m{strnum} ADDED TO OWN:\33[33:1:15m {card[Card.name]}\33[0m (\33[38:5:249m{card[Card.setcode]}\33[0m)')

            [self.scryfall_ids.add(x) for x in arrived_scryfall_ids]

            q: str = 'select scryfall_id from cards'
            exists: set[str] = {x[0] for x in MTGData.cursor.execute(q).fetchall()}
            kill: set[str] = {x for x in self.scryfall_ids if x not in exists}
            [self.scryfall_ids.remove(x) for x in kill]

            self.save_state_to_file()
            Owned.textfile_updated = True

    @staticmethod
    def get_owned() -> set[str]:
        if not Owned.textfile_imported:
            Owned().import_textfile()

        return Owned.scryfall_ids


    @staticmethod
    def get_owned_names() -> set[str]:
        if not Owned.names_imported:
            Owned().import_names()

        return Owned.all_names

    @staticmethod
    def add_to_textfile(card_data: tuple, save: bool = True):
        if not Owned.textfile_imported:
            Owned().import_textfile()

        scry: str = card_data[Card.scryfall_id]
        if scry not in Owned.scryfall_ids:
            Owned.scryfall_ids.add(scry)
            Owned.save_state_to_file() if save else ...

    @staticmethod
    def remove_from_textfile(card_data: tuple, save: bool = True):
        if not Owned.textfile_imported:
            Owned().import_textfile()

        scry: str = card_data[Card.scryfall_id]
        if scry in Owned.scryfall_ids:
            Owned.scryfall_ids.remove(scry)
            Owned.save_state_to_file() if save else ...

    @staticmethod
    def save_state_to_file():
        with open(Owned.path, 'w') as f:
            f.write(','.join(Owned.scryfall_ids))

class CardMarketPrices:
    from useful.update_database import price_datas
    database_integrity(price_datas)
    fetched_setcodes: set[str] = set()
    setcode_bag: dict = {}
    connection = None
    cursor = None

def get_prices(card_data: tuple) -> tuple[float, float]:
    setcode: str = card_data[Card.setcode]
    scryid: str = card_data[Card.scryfall_id]
    obj = CardMarketPrices
    if setcode in obj.setcode_bag:
        return obj.setcode_bag[setcode].get(scryid, (0.0, 0.0,))

    elif setcode not in obj.fetched_setcodes:
        obj.fetched_setcodes.add(setcode)
        if obj.connection is None:
            from useful.update_database import price_datas
            obj.connection = sqlite3.connect(price_datas)
            obj.cursor = obj.connection.cursor()

        q: str = 'select "name" from sqlite_master where type="table" and "name" is (?)'
        v: tuple = setcode,
        if obj.cursor.execute(q, v).fetchone():
            q: str = f'select scryfall_id, regular, foil from "{setcode}"'
            all_prices: list = obj.cursor.execute(q).fetchall()
            obj.setcode_bag[setcode] = {scry: (reg or 0.0, foil or 0.0) for scry, reg, foil in all_prices}
            return obj.setcode_bag[setcode].get(scryid, (0.0, 0.0,))

    return 0.0, 0.0,

def get_regular_price(card_data: tuple) -> float:
    reg, _ = get_prices(card_data)
    return reg

def get_foil_price(card_data: tuple) -> float:
    _, foil = get_prices(card_data)
    return foil

def card_owned(card_data: tuple) -> bool:
    if not Owned.textfile_imported:
        Owned.get_owned()

    return card_data[Card.scryfall_id] in Owned.scryfall_ids

def name_owned(card_data: tuple) -> bool:
    if not Owned.names_imported:
        Owned.get_owned_names()

    return card_data[Card.name] in Owned.all_names