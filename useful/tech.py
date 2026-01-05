from PIL import Image
import os

def add(n: int | float, factor: float | None = None, min_add: int | None = None, max_add: int | None = None, max_val: int | None = None) -> int:
    incr: int = 0
    if factor:
        incr += int(n * factor)
    if min_add and incr < min_add:
        incr = min_add
    if max_add and incr > max_add:
        incr = max_add
    if max_val:
        return min(255, min(max_val, n + incr))
    else:
        return min(255, n + incr)


def sub(n: int, factor: float | None = None, min_sub: int | None = None, max_sub: int | None = None, min_val: int | None = None) -> int:
    incr: int = 0
    if factor:
        incr += int(n * abs(factor))
    if min_sub and incr < min_sub:
        incr = min_sub
    if max_sub and incr > max_sub:
        incr = max_sub
    if min_val:
        return max(0, max(min_val, n - incr))
    else:
        return max(0, n - incr)

def shrinking_rect(contract: int, width: int, height: int) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = contract, contract, (width - 1) - contract, (height - 1) - contract
    if x1 >= x2:
        x1 = max(0, (width - 1) // 2)
        x2 = min(width - 1, x1 + 1)

    if y1 >= x2:
        y1 = max(0, (height - 1) // 2)
        y2 = min(height - 1, y1 + 1)

    return x1, y1, x2, y2


def sub_rgba(r, g, b, a, **kwargs) -> tuple[int, int, int, int]:
    return sub(r, **kwargs), sub(g, **kwargs), sub(b, **kwargs), sub(a, **kwargs)

def add_rgba(r, g, b, a, **kwargs) -> tuple[int, int, int, int]:
    return add(r, **kwargs), add(g, **kwargs), add(b, **kwargs), add(a, **kwargs)

def add_rgb(r, g, b, **kwargs) -> tuple[int, int, int]:
    return add(r, **kwargs), add(g, **kwargs), add(b, **kwargs)

def sub_rgb(r, g, b, **kwargs) -> tuple[int, int, int]:
    return sub(r, **kwargs), sub(g, **kwargs), sub(b, **kwargs)

def go_n(ix: int, width: int = 0) -> int:
    return ix - width

def go_s(ix: int, width: int = 0) -> int:
    return ix + width

def go_w(ix: int, width: int = 0) -> int:
    return ix - 1 + width

def go_e(ix: int, width: int = 0) -> int:
    return ix + 1 + width

def go_nw(ix: int, width: int = 0) -> int:
    return go_n(ix, width) - 1

def go_ne(ix: int, width: int = 0) -> int:
    return go_n(ix, width) + 1

def go_sw(ix: int, width: int = 0) -> int:
    return go_s(ix, width) - 1

def go_se(ix: int, width: int = 0) -> int:
    return go_s(ix, width) + 1

def all_navs(ix: int, width: int = 0) -> tuple:
    return (ix, go_w(ix, width), go_n(ix, width), go_e(ix, width), go_s(ix, width),
            go_nw(ix, width), go_ne(ix, width), go_se(ix, width), go_sw(ix, width))

def get_index(x: int, y: int, width: int) -> int:
    return (y * width) + x

def get_xy(index: int, width: int) -> tuple:
    y: int = index // width
    x: int = index - (y * width)
    return x, y

def crop_lft_top_rgt_btm(indexes, width: int) -> tuple:
    min_y: int = width * width
    min_x: int = width * width
    max_y: int = -1
    max_x: int = -1
    for ix in indexes:
        x, y = get_xy(ix, width=width)

        min_y = min(y, min_y)
        min_x = min(x, min_x)

        max_y = max(y, max_y)
        max_x = max(x, max_x)

    return min_x, min_y, max_x, max_y

def least_crop_size(indexes, org_width: int) -> tuple:
    min_x, min_y, max_x, max_y = crop_lft_top_rgt_btm(indexes, width=org_width)
    return max_x - min_x, max_y - min_y


def extract_symbols(path: str, outer_rgb: tuple = (255, 255, 255), **kwargs) -> list:
    if not os.path.exists(path):
        print(f'path missing: {path}')
        return []

    def human_sorted(symbols: list):
        symbols.sort(key=lambda box: box['crop'][0])
        rows: dict = {}
        for box in symbols:
            crop_lft, crop_top, crop_rgt, crop_btm = box['crop']
            box_centy: int = crop_top + (box['im'].height // 2)
            for (top, btm) in rows:
                if top < box_centy < btm:
                    rows[(top, btm)].append(box)
                    break
            else:
                rows[(crop_top, crop_btm)]: list = [box]

        [symbols.pop(n) for n in range(len(symbols) -1, -1, -1)]

        keys: list = list(rows.keys())
        keys.sort(key=lambda y1y2: y1y2[0])
        for key in keys:
            rows[key].sort(key=lambda box: box['crop'][0])
            for box in rows[key]:
                symbols.append(box['im'])


    im = Image.open(path)
    w, h = im.width, im.height

    datas: list = [rgba for rgba in im.getdata()]
    white: tuple = outer_rgb
    block: set[int] = set()
    symbols: list = []

    for y in range(h):
        for x in range(w):
            ix: int = get_index(x, y, width=w)
            if ix in block:
                continue
            elif datas[ix][:3] == white:
                block.add(ix)
                continue

            new_dat: dict = {}
            roads: set[int] = {ix}
            while roads:
                ix = next(iter(roads))
                roads.remove(ix)
                for ix in all_navs(ix, width=w):
                    if ix not in block:
                        block.add(ix)
                    else:
                        continue

                    col: tuple = datas[ix]
                    if col[:3] == white:
                        continue

                    new_dat[ix]: tuple = col
                    datas[ix]: tuple = white
                    roads.add(ix)

            if new_dat:
                min_w, min_h = least_crop_size(new_dat, org_width=w)
                if (min_w * min_h < 200) or (min_w < 10 or min_h < 10):
                    continue

                new_im = Image.new(mode='RGBA', size=(min_w, min_h), color=white)
                new_datas: list = [white] * (new_im.width * new_im.height)

                crop_lft, crop_top, crop_rgt, crop_btm = crop_lft_top_rgt_btm(new_dat, width=w)
                y_delta: int = crop_top + 1
                x_delta: int = crop_lft + 1
                for ix, col in new_dat.items():
                    org_x, org_y = get_xy(ix, width=w)
                    new_x: int = org_x - x_delta
                    new_y: int = org_y - y_delta
                    new_ix: int = get_index(new_x, new_y, width=min_w)
                    new_datas[new_ix]: tuple = col

                new_im.putdata(new_datas)
                symbols.append(dict(im=new_im, crop=(crop_lft, crop_top, crop_rgt, crop_btm)))

    human_sorted(symbols)
    return symbols

def scramled_images(coldat: dict[str, dict], w: int = 50, h: int = 50, max_cols: int = 8, outer_rgb: tuple = (255, 255, 255), void_rgb: tuple = (0, 0, 0), **kwargs):
    chars: list = list('ABCDEFGHIJLKJMNOPQRSTUVWXY')
    chars = chars[:min(len(chars), max_cols)]
    void_char: str = 'Z'
    void_rgba: tuple = void_rgb[0], void_rgb[1], void_rgb[2], 0
    for color in coldat:
        im = coldat[color]['im']
        if im.width != w or im.height != h:
            if im.width == im.height:
                im.thumbnail(size=(w, h), resample=Image.Resampling.LANCZOS)
            if im.width != im.height:
                im = im.resize(size=(w, h), resample=Image.Resampling.LANCZOS)

        void: set[int] = set()
        datas: dict = {n: rgba[:3] for n, rgba in enumerate(im.getdata())}

        if outer_rgb == (255, 255, 255):
            for y in range(h):
                for x in range(w):
                    ix: int = get_index(x, y, width=w)
                    if ix in void:
                        continue
                    elif sum(datas[ix]) >= 750:
                        void.add(ix)
                    else:
                        break

                for x in range(w - 1, -1, -1):
                    ix: int = get_index(x, y, width=w)
                    if ix in void:
                        continue
                    elif sum(datas[ix]) >= 750:
                        void.add(ix)
                    else:
                        break

            for x in range(w):
                for y in range(h):
                    ix: int = get_index(x, y, width=w)
                    if ix in void:
                        continue
                    elif sum(datas[ix]) >= 750:
                        void.add(ix)
                    else:
                        break

                for y in range(h - 1, -1, -1):
                    ix: int = get_index(x, y, width=w)
                    if ix in void:
                        continue
                    elif sum(datas[ix]) >= 750:
                        void.add(ix)
                    else:
                        break
        else:
            for y in range(h):
                for x in range(w):
                    ix: int = get_index(x, y, width=w)
                    if ix in void:
                        continue
                    elif datas[ix] == outer_rgb:
                        void.add(ix)
                    else:
                        break

                for x in range(w - 1, -1, -1):
                    ix: int = get_index(x, y, width=w)
                    if ix in void:
                        continue
                    elif datas[ix] == outer_rgb:
                        void.add(ix)
                    else:
                        break

            for x in range(w):
                for y in range(h):
                    ix: int = get_index(x, y, width=w)
                    if ix in void:
                        continue
                    elif datas[ix] == outer_rgb:
                        void.add(ix)
                    else:
                        break

                for y in range(h - 1, -1, -1):
                    ix: int = get_index(x, y, width=w)
                    if ix in void:
                        continue
                    elif datas[ix] == outer_rgb:
                        void.add(ix)
                    else:
                        break

        pixels: int = len(datas) - 1
        roads: set[int] = {ix for ix in void}
        block: set[int] = set()
        while roads:
            ix = next(iter(roads))
            roads.remove(ix)
            for ix in all_navs(ix, width=w):
                if ix in block:
                    continue

                block.add(ix)
                if ix < 0 or ix > pixels:
                    continue

                elif datas[ix] == outer_rgb:
                    roads.add(ix)
                    void.add(ix)

        rgb_count: dict = {}
        for ix, rgb in datas.items():
            if ix in void:
                datas[ix] = void_rgba
            else:
                if rgb not in rgb_count:
                    rgb_count[rgb] = 1
                else:
                    rgb_count[rgb] += 1

        tmp = [(rgb, count) for rgb, count in rgb_count.items()]
        tmp.sort(key=lambda rgb_count: rgb_count[1], reverse=True)
        tmp = tmp[:len(chars)]
        rgb_sums: list | tuple = [((*rgb, 255), sub_rgb(*rgb, factor=0.05, min_sub=5)) for rgb, _ in tmp]
        rgb_sums.sort(key=lambda rgb_sum: sum(rgb_sum[1]), reverse=True)

        rgba_char: dict = {rgba: char for (rgba, _), char in zip(rgb_sums, chars)}
        rgba_char[void_rgba]: str = void_char
        for ix, src_rgb in datas.items():
            if ix in void:
                continue

            for dst_rgba, darker_rgb in rgb_sums:
                if all(src_rgb[n] >= darker_rgb[n] for n in range(3)):
                    datas[ix] = dst_rgba
                    break
            else:
                diffs: list = []
                for dst_rgba, darker_rgb in rgb_sums:
                    r1, g1, b1 = src_rgb
                    r2, g2, b2 = dst_rgba[:3]
                    rdiff = abs(r1 - r2)
                    gdiff = abs(g1 - g2)
                    bdiff = abs(b1 - b2)
                    diffs.append((dst_rgba, max(rdiff, gdiff, bdiff)))

                diffs.sort(key=lambda diff: diff[1])
                if diffs[0][1] < 25:
                    datas[ix] = diffs[0][0]
                else:
                    datas[ix] = void_rgba

        final: str = ''
        prev: None | tuple = None
        count: int = 0
        for _, rgba in datas.items():
            if rgba == prev:
                count += 1
            else:
                if count == 0:
                    prev, count = rgba, 1
                else:
                    final += f'{rgba_char[prev]}{count}'
                    prev, count = rgba, 1

        final += f'{rgba_char[prev]}{count}'
        coldat[color]['dat']: str = final
        [coldat[color].update({char: rgba}) for rgba, char in rgba_char.items()]



def printout_scrablmed_images(names: list | None = None, **kwargs) -> dict:
    names = names or []
    symbols: list[Image.Image] = extract_symbols(**kwargs)
    coldat: dict = {names[n] if len(names) > n else str(n): dict(im=im) for n, im in enumerate(symbols)}
    scramled_images(coldat, **kwargs)
    coldat = {k: {kk: vv for kk, vv in v.items() if kk != 'im'} for k, v in coldat.items() if k in names}
    print(f'coldat: dict = {coldat}')
    return coldat

# printout_scrablmed_images(path='/home/plutonergy/tmp/2222/Mana.svg', names=['waste', 'white', 'blue', 'green', 'mtg', 'black', 'red'], max_cols=8)
# printout_scrablmed_images(path='/home/plutonergy/Pictures/w-wubrg.png', names=['waste', 'white', 'blue', 'black', 'red', 'green'])
#names: list[str] = [str(n) for n in range(21)] + list('XYZ') + ['W', 'U', 'B', 'R', 'G', 'S'] + ['W/U', 'W/B', 'U/B', 'U/R', 'B/R', 'B/G', 'R/W', 'R/G', 'G/W', 'G/U'] + ['2/W', '2/U', '2/B', '2/R', '2/G'] + ['W/P', 'U/P', 'B/P', 'R/P', 'G/P'] + ['W/U/P', 'W/B/P', 'U/B/P', 'U/R/P', 'B/R/P', 'B/G/P', 'R/G/P', 'R/W/P', 'G/W/P', 'G/U/P', 'C']
#printout_scrablmed_images(path='/home/plutonergy/tmp/2222/symbols.webp', names=[x.upper() for x in names], max_cols=8)

def alter_stylesheet(stylesheet: str, key: str, val: str):
    parts: list[str] = stylesheet.split(';')
    for n, string in enumerate(parts):
        if ':' in string:
            part: str = string[:string.find(':')]
            if part.startswith(key):
                parts[n]: str = f'{key}:{val}'
                break
    else:
        parts.append(f'{key}:{val}')

    return ';'.join(parts)