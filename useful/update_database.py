import sqlite3, os, time

names: list[str] = __file__.split(os.sep)
subdir: str = os.sep.join(x for x in names[:-2])

db_path_card_datas: str = f'{subdir}{os.sep}quick_db.sqlite'
legal_card_datas: str = f'{subdir}{os.sep}legal_db.sqlite'
user_datas: str = f'{subdir}{os.sep}user_datas.sqlite'
price_datas: str = f'{subdir}{os.sep}setcode_prices.sqlite'
fresh_databases: str = f'{subdir}{os.sep}fresh_database.zip'

CARD_COLUMNS: set = {'power', 'toughness', 'cmc', 'name', 'type', 'setcode', 'types', 'text', 'artist', 'scryfall_id',
                     'keywords', 'layout', 'side', 'frame_effects', 'number', 'loyalty', 'rarity', 'mana_cost',
                     'colors', 'color_identity'}

SET_COLUMNS: set = {'name', 'releasedate_epoch', 'releasedate_string', 'setcode', 'type'}

# BLOCK STUPID SHIT
BLOCK_KEYWORDS: set = {'The List', 'Mystery Booster', 'Renaissance', 'Rinascimento'}

BLOCK_TYPES: set = {'archenemy', 'arsenal', 'box', 'duel_deck', 'from_the_vault', 'funny', 'memorabilia', 'minigame',
                    'premium_deck', 'promo', 'spellbook', 'starter', 'token', 'vanguard', 'planechase'}

BLOCK_SETCODES: set = {'4BB', 'FBB'}

KEEP_SETCODES: set = {'PHPR', 'ITP', 'CED', 'CEI'}
KEEP_KEYWORDS: set = {'Portal', }

def make_quick_db():
    print(f'cards-database missing, creating a new', end='', flush=True)
    start: float = time.time()

    src_db_path: str = '/home/plutonergy/Coding/PLMTG_v4/AllPrintings.sqlite'
    src_connection = sqlite3.connect(src_db_path)
    src_cursor = src_connection.cursor()

    class SrcCard:
        """"""

    class SrcSet:
        """"""

    class DstCard:
        """"""

    class DstSet:
        """"""

    dst_connection = sqlite3.connect(db_path_card_datas)
    dst_cursor = dst_connection.cursor()

    q: str = f'PRAGMA table_info(cards)'
    cards_pragma: list[tuple] = src_cursor.execute(q).fetchall()
    [setattr(SrcCard, x[1], x[0]) for x in cards_pragma]

    q: str = f'PRAGMA table_info(sets)'
    sets_pragma: list[tuple] = src_cursor.execute(q).fetchall()
    [setattr(SrcSet, x[1], x[0]) for x in sets_pragma]

    q: str = 'select * from sets where setcode is not null'
    src_sets: list[tuple] = [x for x in src_cursor.execute(q).fetchall()]
    for n in range(len(src_sets) -1, -1, -1):
        tup = src_sets[n]
        if tup[SrcSet.setcode] in KEEP_SETCODES:
            continue
        for keyword in KEEP_KEYWORDS:
            if tup[SrcSet.name].startswith(keyword):
                break
        else:
            if tup[SrcSet.setcode] in BLOCK_SETCODES:
                src_sets.pop(n)
            elif tup[SrcSet.type] in BLOCK_TYPES:
                src_sets.pop(n)
            else:
                for keyword in BLOCK_KEYWORDS:
                    if tup[SrcSet.name].startswith(keyword):
                        src_sets.pop(n)
                        break


    good_setcodes: set = {x[SrcSet.setcode] for x in src_sets}
    placehldrs: str = ','.join(['?'] * len(good_setcodes))

    q: str = f'select * from cards where setcode in ({placehldrs})'
    src_cards: list[tuple] = [x for x in src_cursor.execute(q, list(good_setcodes)).fetchall()]

    src_cursor.close()
    src_connection.close()

    card_cols: list[str] = sorted(list(CARD_COLUMNS))
    set_cols: list[str] = sorted(list(SET_COLUMNS))

    with dst_connection:
        q: str = 'drop table if exists cards'
        dst_cursor.execute(q)

        q: str = 'drop table if exists sets'
        dst_cursor.execute(q)

        colname_type: dict = {x[1]: x[2] for x in cards_pragma if x[1] in card_cols}
        name_type: list[str] = [f'{colname} {colname_type[colname]}' for colname in card_cols]
        q: str = f'create table cards ({",".join(name_type)})'
        dst_cursor.execute(q)

        colname_type: dict = {x[1]: x[2] for x in sets_pragma if x[1] in set_cols}
        name_type: list[str] = [f'{colname} {colname_type[colname]}' for colname in set_cols]
        q: str = f'create table sets ({",".join(name_type)})'
        dst_cursor.execute(q)

    q: str = f'PRAGMA table_info(cards)'
    cards_pragma: list[tuple] = dst_cursor.execute(q).fetchall()
    [setattr(DstCard, x[1], x[0]) for x in cards_pragma]

    q: str = f'PRAGMA table_info(sets)'
    sets_pragma: list[tuple] = dst_cursor.execute(q).fetchall()
    [setattr(DstSet, x[1], x[0]) for x in sets_pragma]

    many_cards: list[tuple] = []
    dst_src: dict[int, int] = {getattr(SrcCard, colname): getattr(DstCard, colname) for colname in CARD_COLUMNS}
    for card in src_cards:
        v: list = [None] * len(card_cols)
        for src_ix, dst_ix in dst_src.items():
            v[dst_ix] = card[src_ix]

        many_cards.append(tuple(v))

    many_sets: list[tuple] = []
    dst_src: dict[int, int] = {getattr(SrcSet, colname): getattr(DstSet, colname) for colname in SET_COLUMNS}
    for setdata in src_sets:
        v: list = [None] * len(SET_COLUMNS)
        for src_ix, dst_ix in dst_src.items():
            v[dst_ix] = setdata[src_ix]

        many_sets.append(tuple(v))

    with dst_connection:
        marks: list = ['?'] * len(card_cols)
        q: str = f'insert into cards values({",".join(marks)})'
        dst_cursor.executemany(q, many_cards)

        marks: list = ['?'] * len(set_cols)
        q: str = f'insert into sets values({",".join(marks)})'
        dst_cursor.executemany(q, many_sets)

    dst_cursor.close()
    dst_connection.close()
    print(f' ({round(time.time() - start, 4)} sec)', flush=True)

def make_quick_legal_db():
    print(f'legal-database missing, creating a new', end='', flush=True)
    start: float = time.time()

    src_db_path: str = '/home/plutonergy/Coding/PLMTG_v4/legalities.sqlite'
    src_connection = sqlite3.connect(src_db_path)
    src_cursor = src_connection.cursor()

    cards_connection = sqlite3.connect(db_path_card_datas)
    cards_cursor = cards_connection.cursor()

    q: str = 'select "name" from cards'
    all_names: set[str] = {x[0] for x in cards_cursor.execute(q).fetchall()}

    q: str = 'select name, csv_status from legalities'
    name_csv: dict[str, str] = {name: csv for name, csv in src_cursor.execute(q).fetchall() if name in all_names}

    src_cursor.close()
    src_connection.close()

    cards_cursor.close()
    cards_connection.close()

    dst_connection = sqlite3.connect(legal_card_datas)
    dst_cursor = dst_connection.cursor()

    with dst_connection:
        q: str = 'drop table if exists legalities'
        dst_cursor.execute(q)

        dst_cursor.execute('create table legalities (name TEXT, csv_status TEXT)')
        many: list = [(name, csv_status) for name, csv_status in name_csv.items()]
        q: str = 'insert into legalities values(?,?)'
        dst_cursor.executemany(q, many)

    print(f' ({round(time.time() - start, 4)} sec)', flush=True)


def make_prices_db():
    from useful.database import MTGData
    dst_connection = sqlite3.connect(price_datas)
    dst_cursor = dst_connection.cursor()

    q: str = 'select scryfall_id from cards where (side is "a" or side is null)'
    scry_ids: set = {x[0] for x in MTGData.cursor.execute(q).fetchall()}

    path: str = '/home/plutonergy/Coding/PLMTG_v4/AllPrintings.sqlite'
    src_conn = sqlite3.connect(path)
    src_cursor = src_conn.cursor()
    q: str = 'select uuid, scryfall_id from cards'
    uuid_scry: dict = {x[0]: x[1] for x in src_cursor.execute(q).fetchall() if x[1] in scry_ids}
    requested_uuids: set[str] = set(uuid_scry.keys())
    src_cursor.close()
    src_conn.close()

    path: str = '/home/plutonergy/Coding/PLMTG_v4/splitprice.sqlite'
    src_conn = sqlite3.connect(path)
    src_cursor = src_conn.cursor()
    q: str = 'select "name" from sqlite_master where type="table" and "name" != "sqlite_sequence"'
    setcodes: list = [x[0] for x in src_cursor.execute(q).fetchall() if x[0] in MTGData.SETCODES]
    setcodes.sort(key=lambda x: MTGData.SETCODE_EXPNAME[x])
    setcode_box: dict[str, list] = {setcode: [] for setcode in setcodes if len(setcode) <= 4}
    src_col_ix = lambda: None
    src_cols: list = sorted(['uuid', 'unixTime', 'euReg', 'euFoil'])
    [setattr(src_col_ix, col, ix) for ix, col in enumerate(src_cols)]

    exp_names_max: int = max(len(x) for x in [MTGData.SETCODE_EXPNAME[y] for y in setcode_box])

    dst_cols: list = sorted(['scryfall_id', 'regular', 'foil'])
    dst_col_ix = lambda: None
    [setattr(dst_col_ix, col, ix) for ix, col in enumerate(dst_cols)]

    for setcode, box in setcode_box.items():
        start_time: float = time.time()
        exp_name: str = MTGData.SETCODE_EXPNAME[setcode]
        print(f'{exp_name} {" " * (exp_names_max - len(exp_name))} ', end='', flush=True)

        q = f'select {", ".join(src_cols)} from "{setcode}"'
        datas: list = src_cursor.execute(q).fetchall()
        datas.sort(key=lambda x: x[src_col_ix.unixTime], reverse=True)

        prevs: set[str] = set()
        for data in datas:
            uuid: str = data[src_col_ix.uuid]
            if uuid in prevs:
                continue

            prevs.add(uuid)
            if uuid not in requested_uuids:
                continue
            elif all(not data[x] for x in [src_col_ix.euReg, src_col_ix.euFoil]):
                continue

            new: list = [None] * len(dst_cols)
            new[dst_col_ix.scryfall_id]: str = uuid_scry[uuid]
            new[dst_col_ix.regular]: float | None = data[src_col_ix.euReg]
            new[dst_col_ix.foil]: float | None = data[src_col_ix.euFoil]
            box.append(tuple(new))

        with dst_connection:
            q = f'drop table if exists "{setcode}"'
            dst_cursor.execute(q)
            cols_string: str = ', '.join([f'{x} {"TEXT" if x in "scryfall_id" else "FLOAT"}' for x in dst_cols])
            q = f'create table "{setcode}" ({cols_string})'
            dst_cursor.execute(q)
            marks = ','.join(['?'] * len(dst_cols))
            q = f'insert into "{setcode}" values ({marks})'
            dst_cursor.executemany(q, box)

        time_taken: float = time.time() - start_time
        print(f' {" " * (5 - len(str(len(box))))}{len(box)} prices ({round(time_taken, 4)} sec)', flush=True)


    src_cursor.close()
    src_conn.close()

    dst_cursor.close()
    dst_connection.close()





















