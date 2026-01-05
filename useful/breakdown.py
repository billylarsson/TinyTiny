from useful.database import MTGData,Owned,Card

class SmartVal:
    def __init__(self, key: str, sep: str, val):

        if isinstance(val, bool) and '!=' in sep:
            # simplifying True/False scenarios
            if val:
                sep, val = '==', False
            else:
                sep, val = '==', True

        self.key: str = key
        self.sep: str = '==' if sep in '=' else sep
        self.op, self.operator = self.sep, self.sep  # assuming op/operator would be used by devs
        self.val = val

    def __iter__(self):
        args: tuple = self.key, self.sep, self.val
        return iter(args)


class SmartKey:
    trailing: bool = False
    seps: tuple = '==', '!=', '>=', '<=', '>', '<', '='
    def __init__(self,
                 key: str,
                 keys = None,
                 seps: tuple | None = None,
                 default: bool = False,
                 auto_sep: str | None = None,
                 min_reach: int = 0,
                 ):
        self.key: str = key
        self.keys: set = {self.key}
        if isinstance(keys, (set, tuple, list, dict)):
            [self.keys.add(key) for key in keys]

        self.seps: tuple = seps or self.seps
        self.default: bool = default
        self.auto_sep: str | None = auto_sep
        self.min_reach: int = max(1, (min_reach or len(self.key)))
        self.min_reach = min(self.min_reach, len(self.key))


    def translate_values(self, *args, **kwargs) -> list[SmartVal]:
        vals: list[SmartVal] = []
        return vals

    def next_fwd_stop(self, text: str) -> int:
        marks: list[str] = [' '] + list(self.seps)
        walls: list[int] = [text.find(mark) for mark in marks if mark in text]
        rgt: int = min(walls) if walls else len(text)
        return rgt

    def enough_key_reach(self, fuzzy_key: str) -> bool:
        for any_key in self.keys:
            arm: int = min(len(fuzzy_key), self.min_reach, len(any_key))
            if arm < self.min_reach:
                continue

            for n, char in enumerate(fuzzy_key):
                if n >= len(any_key) or char not in any_key[n]:
                    break
            else:
                if fuzzy_key[:arm] in any_key[:arm]:
                    return True
        return False


    def get_next_sep(self, text: str) -> str | None:
        for sep in self.seps:
            if text.startswith(sep):
                return sep
        return self.auto_sep


class BoolKey(SmartKey):
    key_type = bool
    trailing: bool = False
    seps: tuple = '==', '!=', '=',

    def translate_values(self, key: str, sep: str, text: str, auto_sep: bool = False, **kwargs) -> list[SmartVal]:
        vals: list[SmartVal] = []

        if auto_sep:
            smartval: SmartVal = SmartVal(key, sep, val=True)
            vals.append(smartval)
        else:
            if text in ['true', 'false']:
                smartval: SmartVal = SmartVal(key, sep, val=text in 'true')
                vals.append(smartval)

        return vals

class IntKey(SmartKey):
    key_type = int
    trailing: bool = True

    def translate_values(self, key: str, sep: str, text: str, limit: int = 100, **kwargs) -> list[SmartVal]:
        vals: list[SmartVal] = []
        if '-' in text:
            parts: list[str] = text.split('-')
            if len(parts) == 2:
                if parts[0].isdigit() and parts[1].isdigit():
                    beg: int = min(int(parts[0]), int(parts[1]))
                    end: int = max(int(parts[0]), int(parts[1]))
                    for val in range(beg, min(end, beg + limit) + 1):
                        smv: SmartVal = SmartVal(key, sep, val=val)
                        vals.append(smv)

        else:
            val = text.strip()
            if val and val.isdigit():
                smv: SmartVal = SmartVal(key, sep, val=int(val))
                vals.append(smv)

        return vals

class StrKey(SmartKey):
    key_type = str
    trailing: bool = False

    def translate_values(self, key: str, sep: str, text: str, **kwargs) -> list[SmartVal]:
        vals: list[SmartVal] = []
        text: str = text.strip()
        if text.startswith('"') and text.endswith('"'):
            if len(text) > 2:
                smv: SmartVal = SmartVal(key, sep, val=text[1: -1])
                vals.append(smv)
        else:
            if text:
                smv: SmartVal = SmartVal(key, sep, val=text)
                vals.append(smv)
        return vals

class SmartArgs:
    results: list[SmartVal] = []
    sep_marks: str = ' _,+'

    def __init__(self, query: str, smartkeys: list[SmartKey], singleton: bool = True):
        self.query: str = query
        self.singleton: bool = singleton

        self.smartkeys: list[SmartKey] = [smartkey for smartkey in smartkeys]
        self.smartkeys.sort(key=lambda x: x.key)

        self.results: list[SmartVal] = self.extract_values()

        for smk in self.smartkeys:
            if smk.default and smk.auto_sep:
                msk_query: str = self.masked_quotations(self.query)
                parts: list[str] = ['']
                for n, char in enumerate(msk_query):
                    if char not in self.sep_marks:
                        parts[-1] += self.query[n]

                    elif parts[-1]:
                        parts.append('')

                parts = [f'{smk.key}{smk.auto_sep}{part}' for part in parts if part.strip()]
                if parts:
                    self.query = ' '.join(parts)
                    self.results += self.extract_values()
                    break

        self.results = self.singleton_results(self.results) if singleton else self.results

    def __iter__(self):
        for smartval in self.results:
            yield smartval

    def singleton_results(self, smartvals: list[SmartVal]) -> list[SmartVal]:
        singletons: list[SmartVal] = []
        breakdown: dict = {}
        for smartval in smartvals:
            key, sep, val = smartval.key, smartval.sep, smartval.val
            if key not in breakdown:
                breakdown[key]: dict = {}
            if sep not in breakdown[key]:
                breakdown[key][sep] = set()
            breakdown[key][sep].add(val)

        sorted_keys: list = sorted(list(breakdown.keys()))
        for key in sorted_keys:
            sorted_operators: list = sorted(list(breakdown[key].keys()))
            for operator in sorted_operators:
                types_singleton: set = {str(type(val)) for val in breakdown[key][operator]}
                sorted_types: dict = {str_type: set() for str_type in sorted(types_singleton)}
                for val in breakdown[key][operator]:
                    sorted_types[str(type(val))].add(val)

                for str_type, vals in sorted_types.items():
                    for sorted_val in tuple(sorted(vals)):
                        smartval: SmartVal = SmartVal(key=key, sep=operator, val=sorted_val)
                        singletons.append(smartval)

        return singletons

    def skip_fwd(self, text: str) -> int:
        """returns how many chars in self.sepmarks from the left that needs to be skipped til relevant char appears"""
        return len(text) - len(text.lstrip(self.sep_marks))

    def extract_values(self) -> list[SmartVal]:
        results: list[SmartVal] = []
        poles: list[int] = self.get_poles()
        always_space: set[int] = set()
        lft: int = 0
        while lft < len(self.query):
            query: str = self.masked_quotations(self.query)
            lft += self.skip_fwd(text=query[lft:])
            rgt_poles: list[int] = [pole - 1 for pole in poles if pole - 1 > lft]
            rgt_wall: int = min(rgt_poles) if rgt_poles else len(query)
            for smk in self.smartkeys:

                rgt: int = lft + smk.next_fwd_stop(query[lft: rgt_wall])
                fuzzy_key: str = self.query[lft: rgt]
                if not smk.enough_key_reach(fuzzy_key):
                    continue

                key_lft: int = lft
                key_rgt: int = rgt

                rgt += self.skip_fwd(text=query[rgt:])
                sep: str | None = smk.get_next_sep(query[rgt: rgt_wall])
                sep_present: bool = sep and query[rgt:].startswith(sep)
                using_auto_sep: bool = sep and not sep_present

                if sep_present:
                    lft = (rgt + query[rgt:].find(sep) + len(sep))
                elif using_auto_sep:
                    lft = rgt if smk.trailing else key_lft
                else:
                    continue

                lft += self.skip_fwd(text=query[lft:])
                text: str = query[lft: rgt_wall]
                if not text.lstrip(self.sep_marks):
                    continue

                if any(mark in text for mark in self.sep_marks):
                    marks: list = [(mark, text.find(mark)) for mark in self.sep_marks if mark in text]
                    marks.sort(key=lambda x: x[1])
                    rgt_sep, rgt_ix = marks[0]
                    text: str = self.query[lft: lft + rgt_ix]
                    space_sep: bool = rgt_sep in ' '
                    if not text.lstrip(self.sep_marks):
                        continue
                else:
                    text: str = self.query[lft: rgt_wall]
                    space_sep: bool = False

                kwgs = dict(key=smk.key, sep=sep, text=text, auto_sep=using_auto_sep, limit=100)
                smartvals: list[SmartVal] = smk.translate_values(**kwgs)
                if not smartvals:
                    continue

                results += smartvals
                if not space_sep or smk.trailing:
                    [always_space.add(ix) for ix in range(key_lft, lft)]
                    spaces: str = ' ' * len(query[lft: lft + len(text)])
                    self.query = self.query[:lft] + spaces + self.query[lft + len(text):]
                    lft = key_lft
                    break
                else:
                    spaces: str = ' ' * len(query[key_lft: lft + len(text)])
                    self.query = self.query[:key_lft] + spaces + self.query[lft + len(text):]
                    lft = key_lft
                    break

            else:
                self.query = ''.join(char if ix not in always_space else ' ' for ix, char in enumerate(self.query))
                lft = rgt_wall

        return results

    def masked_quotations(self, text: str, maskchar: str = 'x') -> str:
        while text.count('"') >= 2:
            lft: int = text.find('"')
            rgt: int = text[lft + 1:].find('"') + lft + 2
            exs: str = maskchar * (rgt - lft)
            text = text[:lft] + exs + text[rgt:]

        return text


    def get_poles(self) -> list[int]:
        lft: int = 0
        poles: list[int] = []
        while lft < len(self.query):
            query: str = self.masked_quotations(self.query)
            lft += self.skip_fwd(text=query[lft:])

            for smk in self.smartkeys:
                rgt: int = lft + smk.next_fwd_stop(query[lft:])
                fuzzy_key: str = self.query[lft: rgt]
                if not smk.enough_key_reach(fuzzy_key):
                    continue

                poles.append(lft)
                lft = rgt
                break

            else:
                if ' ' in query[lft:]:
                    lft += query[lft:].find(' ')
                else:
                    break

        return poles

smartkeys: list[SmartKey] = [
    IntKey(key='power', min_reach=1),
    IntKey(key='toughness', min_reach=1),
    IntKey(key='cmc'),
    IntKey(key='number', min_reach=3),

    # IntKey(key='year', min_reach=1),
    StrKey(key='year', min_reach=1),

    BoolKey(key='owned'),
    BoolKey(key='stupid'),
    BoolKey(key='monocolor', min_reach=5),
    BoolKey(key='multicolor', min_reach=6),

    StrKey(key='name', min_reach=1, default=True, auto_sep='=='),
    StrKey(key='setcode', keys={'code'}, min_reach=3),
    StrKey(key='type', keys={'spec', 'specbox', 'type'}),
    StrKey(key='expansion', min_reach=3),
    StrKey(key='artist'),
    StrKey(key='colors', min_reach=3, seps=BoolKey.seps),
    StrKey(key='cost', keys={'costs'}, seps=BoolKey.seps),
    StrKey(key='textbox', min_reach=4, seps=BoolKey.seps),
    StrKey(key='keywords', min_reach=3, seps=BoolKey.seps),
    StrKey(key='rarity', seps=BoolKey.seps),

    StrKey(key='legal', seps=BoolKey.seps),
    StrKey(key='banned', seps=BoolKey.seps),
    StrKey(key='restricted', seps=BoolKey.seps),
]
MTG_TYPES: set[str] = {'artifact', 'battle', 'creature', 'enchantment', 'instant', 'kindred', 'land', 'planeswalker', 'sorcery', 'tribal'}
RARITIES: set[str] = {'mythic', 'rare', 'uncommon', 'common'}
smartkeys += [BoolKey(mtg_type, min_reach=4, auto_sep='=') for mtg_type in MTG_TYPES]
smartkeys += [BoolKey(rarity, min_reach=4, auto_sep='=') for rarity in RARITIES]

def tweak_query(text: str, custom_smartkeys: list[SmartKey] | None = None) -> str:
    parts: list[str] = []
    for part in [part for part in text.split() if part]:
        if part in ['M']:
            parts.append('rarity=mythic')
        elif part in ['R']:
            parts.append('rarity=rare')
        elif part in ['U']:
            parts.append('rarity=uncommon')
        elif part in ['C']:
            parts.append('rarity=common')

        elif len(part) in [3, 4] and all(char.isupper() for char in part):
            parts.append(f'setcode={part}')
        elif part[0].isupper() and part[0].isalpha():
            parts.append(f'expansion={part}')

        else:
            parts.append(part)

    query: str =  ' '.join(parts).lower()
    smvs: list[SmartVal] = SmartArgs(query=query, smartkeys=custom_smartkeys or smartkeys).results
    parts: list[str] = []
    for smv in smvs:
        key, sep, val = smv
        if key == 'colors':
            races = dict(
                esper='WUB',
                grixis='UBR',
                temur='GUR',
                naya='RGW',
                jeskai='URW',
                mardu='RWB',
                sultai='BGU',
                abzan='WBG',
                jund='BRG',
                bant='GWB',
                azorius='UW',
                boros='RW',
                dimir='UB',
                golgari='GB',
                gruul='RG',
                izzet='UR',
                orzhov='WB',
                rakdos='RB',
                selesnya='WG',
                simic='UG'
            )
            if val in races:
                for col in list(races[val]):
                    parts.append(f'{key}{sep}{col}')
            else:
                for col in list(val):
                    parts.append(f'{key}{sep}{col}')
        else:
            parts.append(f'{key}{sep}{val}')

    return ' '.join(parts).lower()


def search_cards(text: str, custom_smartkeys: list[SmartKey] | None = None) -> list:
    cards_queue: list = []
    smvs: list[SmartVal] = SmartArgs(query=text, smartkeys=custom_smartkeys or smartkeys).results
    allowed_setcodes: set[str] = set(MTGData.SETCODE_EXPNAME.keys())
    owned: set[str] = set()
    for smv in smvs:
        key, sep, val = smv

        if key in ['setcode', 'expansion']:
            boxes: list = [dict(setcode=x, expansion=MTGData.SETCODE_EXPNAME[x]) for x in allowed_setcodes]
            for box in boxes:
                if '==' in sep:
                    good: bool = val in box[key].lower()
                elif '!=' in sep:
                    good: bool = val not in box[key].lower()
                elif '>=' in sep:
                    good: bool = val >= box[key].lower()
                elif '<=' in sep:
                    good: bool = val <= box[key].lower()
                elif '>' in sep:
                    good: bool = val > box[key].lower()
                elif '<' in sep:
                    good: bool = val < box[key].lower()
                else:
                    good: bool = False

                if not good and box['setcode'] in allowed_setcodes:
                    allowed_setcodes.remove(box['setcode'])

        elif key in ['year']:
            q: str = 'select setcode, releasedate_string from sets'
            setcode_date: dict = {k: v for k, v in MTGData.cursor.execute(q).fetchall()}
            if len(val) == 4 and val.isdigit():
                setcode_date = {k: v[:4] for k,v in setcode_date.items()}

            elif val.upper() in setcode_date:
                val = setcode_date[val.upper()]

            for setcode, year in setcode_date.items():
                if '==' in sep:
                    good: bool = year == val
                elif '!=' in sep:
                    good: bool = year != val
                elif '>=' in sep:
                    good: bool = val <= year
                elif '<=' in sep:
                    good: bool = val >= year
                elif '>' in sep:
                    good: bool = val < year
                elif '<' in sep:
                    good: bool = val > year
                else:
                    good: bool = False

                if not good and setcode in allowed_setcodes:
                    allowed_setcodes.remove(setcode)

        elif key in ['owned']:
            owned = Owned.get_owned()

        elif key in ['legal', 'banned', 'restricted']:
            if all(bag.legal == {} for name, bag in MTGData.NAME_BAG.items()):
                MTGData.insert_legalities()

    for card_name, bag in MTGData.NAME_BAG.items():
        card: tuple = bag.prefered
        cards: list = [x for x in bag.cards if x[Card.setcode] in allowed_setcodes]
        good: bool = any(cards)
        for smv in smvs:
            if not good or not cards:
                break

            key, sep, val = smv
            if key in ['power', 'toughness', 'cmc']:

                if key in 'cmc':
                    val = int(val)
                    ix: int = Card.cmc
                else:
                    val = float(val)
                    if key in 'power':
                        ix: int = Card.power
                    else:
                        ix: int = Card.toughness

                    if card[ix] is None:
                        good = '!=' in sep
                        continue

                if '==' in sep:
                    good = card[ix] == val
                elif '!=' in sep:
                    good = card[ix] != val
                elif '>=' in sep:
                    good = card[ix] >= val
                elif '<=' in sep:
                    good = card[ix] <= val
                elif '>' in sep:
                    good = card[ix] > val
                elif '<' in sep:
                    good = card[ix] < val

            elif key in ['number']:
                ix: int = Card.number
                if '==' in sep:
                    str_val: str = str(val)
                    cards = [x for x in cards if x[ix] == str_val]
                elif '!=' in sep:
                    str_val: str = str(val)
                    cards = [x for x in cards if x[ix] != str_val]
                else:
                    cards = [x for x in cards if x[ix].isdigit()]
                    if '>=' in sep:
                        cards = [x for x in cards if int(x[ix]) >= val]
                    elif '<=' in sep:
                        cards = [x for x in cards if int(x[ix]) <= val]
                    elif '>' in sep:
                        cards = [x for x in cards if int(x[ix]) > val]
                    elif '<' in sep:
                        cards = [x for x in cards if int(x[ix]) < val]

            elif key in ['name', 'specbox', 'type']:

                if key in 'name':
                    ix: int = Card.name
                else:
                    ix: int = Card.type

                if not isinstance(card[ix], str):
                    good = '!=' in sep
                    continue

                if '==' in sep:
                    good = val in card[ix].lower()
                elif '!=' in sep:
                    good = val not in card[ix].lower()
                elif '>=' in sep:
                    good = val >= card[ix].lower()
                elif '<=' in sep:
                    good = val <= card[ix].lower()
                elif '>' in sep:
                    good = val > card[ix].lower()
                elif '<' in sep:
                    good = val < card[ix].lower()

            elif key in ['artist']:
                ix: int = Card.artist
                if '!=' in sep:
                    cards = [x for x in cards if val not in (x[ix] or '').lower()]
                else:
                    cards = [x for x in cards if x[ix] is not None]
                    if '==' in sep:
                        cards = [x for x in cards if val in x[ix].lower()]
                    elif '>=' in sep:
                        cards = [x for x in cards if val >= x[ix].lower()]
                    elif '<=' in sep:
                        cards = [x for x in cards if val <= x[ix].lower()]
                    elif '>' in sep:
                        cards = [x for x in cards if val > x[ix].lower()]
                    elif '<' in sep:
                        cards = [x for x in cards if val < x[ix].lower()]

            elif key in MTG_TYPES:
                ix: int = Card.types
                if val:
                    cards = [x for x in cards if key in x[ix].lower()]
                else:
                    cards = [x for x in cards if key not in x[ix].lower()]

            elif key in ['textbox', 'keywords', 'colors', 'cost']:
                if key in ['textbox']:
                    ix: int = Card.text
                elif key in ['colors']:
                    ix: int = Card.color_identity
                elif key in ['cost']:
                    ix: int = Card.mana_cost
                else:
                    ix: int = Card.keywords

                if not isinstance(card[ix], str):
                    good = '!=' in sep
                    continue

                if sep in '==':
                    good = val in card[ix].lower()
                else:
                    good = val not in card[ix].lower()

            elif key in ['rarity'] or key in RARITIES:
                ix: int = Card.rarity
                if key in RARITIES:
                    if (val and sep in '==') or (not val and sep in '!='):
                        cards = [x for x in cards if key == x[ix]]
                    else:
                        cards = [x for x in cards if key != x[ix]]
                else:
                    if (val and sep in '==') or (not val and sep in '!='):
                        cards = [x for x in cards if x[ix].startswith(val)]
                    else:
                        cards = [x for x in cards if not x[ix].startswith(val)]

            elif key in ['owned']:
                ix: int = Card.scryfall_id
                if val:
                    cards = [x for x in cards if x[ix] in owned]
                else:
                    cards = [x for x in cards if x[ix] not in owned]

            elif key in ['legal', 'banned', 'restricted']:
                if sep in '==':
                    good = any(fmt.startswith(val) for fmt in bag.legal[key])
                else:
                    good = all(not fmt.startswith(val) for fmt in bag.legal[key])

            elif key in ['stupid']:
                if val:
                    good = bag.is_stupid
                else:
                    good = not bag.is_stupid

            elif key in ['monocolor', 'multicolor']:
                ix: int = Card.colors
                if (val and key in ['monocolor']) or (not val and key in ['multicolor']):
                    cards = [x for x in cards if ',' not in (x[ix] or '')]
                else:
                    cards = [x for x in cards if ',' in (x[ix] or '')]

        if not good or not cards:
            continue
        elif bag.prefered in cards:
            card = bag.prefered
        else:
            for iter_card in cards:
                if MTGData.setcode_type[iter_card[Card.setcode]] in ['expansion', 'core']:
                    card = iter_card
                    break
            else:
                card = cards[0]

        cards_queue.append(dict(card=card, bag=bag, showcase=None))

    return cards_queue

def sort_cards(cards: list[dict], var: str = 'NAME', reverse: bool = False):
    cards.sort(key=lambda x: x['card'][Card.name]) if var not in 'NAME' else ...
    if var in 'NAME':
        cards.sort(key=lambda x: x['card'][Card.name], reverse=reverse)
    elif var in 'RARITY':
        rarity_rank: dict = dict(
            mythic=1,
            rare=2,
            uncommon=3,
            common=4,
            land=5,
            special=6,
        )
        cards.sort(key=lambda x: rarity_rank[x['card'][Card.rarity]], reverse=reverse)
    elif var in 'CMC':
        cards.sort(key=lambda x: x['card'][Card.cmc], reverse=reverse)
    elif var in 'POWER':
        cards.sort(key=lambda x: x['card'][Card.power] or 999, reverse=reverse)
    elif var in 'TOUGHNESS':
        cards.sort(key=lambda x: x['card'][Card.toughness] or 999, reverse=reverse)
    elif var in 'TYPE':
        cards.sort(key=lambda x: x['card'][Card.type] or 999, reverse=reverse)
    elif var in 'COLOR':
        cards.sort(key=lambda x: x['card'][Card.colors] or 'A', reverse=reverse)