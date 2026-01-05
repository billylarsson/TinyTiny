from PIL             import Image
from PyQt6           import QtCore
from PyQt6.QtCore    import QObject, pyqtSignal
from threading       import Lock
from useful.database import Card, MTGData
import certifi, copy, io, json, os, pathlib, ssl, sys, time, urllib.request


class LocalImages:
    parts: list[str] = __file__.split(os.sep)
    subdir: str = os.sep.join(parts[:-2])
    directory: str = f'{subdir}{os.sep}img_dir'

    devs_dir: str = '/home/plutonergy/Pictures/MTG'
    if os.path.exists(devs_dir):
        for walk in os.walk(devs_dir):
            if any(bag for bag in walk[1:]):
                directory: str = devs_dir
                break
            else:
                print(f'mount "{devs_dir}" first or make sure you have at least one dir/file in there...')
                sys.exit()

def get_setcode(card_data: tuple) -> str:
    return card_data[Card.setcode]

def get_expname(card_data: tuple) -> str:
    setcode: str = get_setcode(card_data)
    expname: str = MTGData.SETCODE_EXPNAME[setcode].replace(os.sep, '-')
    return expname

def get_subdir(card_data: tuple) -> str:
    if os.sep in '/':
        setcode: str = get_setcode(card_data)
        expname: str = get_expname(card_data)
        return f'{LocalImages.directory}{os.sep}{setcode} - {expname}'
    else:
        setcode: str = get_setcode(card_data)
        return f'{LocalImages.directory}{os.sep}{setcode}'


def webp_path(card_data: tuple) -> str:
    subdir: str = get_subdir(card_data)
    scryfall_id: str = card_data[Card.scryfall_id]
    side: str | None = card_data[Card.side] or None
    single_sided: bool = card_data[Card.layout] not in ['transform', 'modal_dfc', 'meld']
    if side and single_sided:
        side = 'a'

    path: str = f'{subdir}{os.sep}{scryfall_id}'
    path += f'_side_{side}_large.webp' if side else '_large.webp'
    return path



class Worker(QObject):
    stop_downloading = pyqtSignal(bool)
    start_downloading = pyqtSignal(tuple)
    finished = pyqtSignal(bool)

    def __init__(self, card_data: tuple, lock: Lock, *args, **kwargs):
        self.errors: list[str] = []
        self.card_data: tuple = copy.deepcopy(card_data)
        self.is_halted: bool = False
        self.lock: Lock = lock
        super().__init__(*args, **kwargs)

    @QtCore.pyqtSlot()
    def run(self):
        self.start_downloading.connect(self.init_download)
        self.stop_downloading.connect(self.change_momentum)
        self.start_downloading.emit(self.card_data)

    def init_download(self, card_data: tuple):
        self.card_data: tuple = copy.deepcopy(card_data)
        successful = self.start_scryfall_downloading()
        if self.is_halted is False and self.errors:
            print('\n'.join(self.errors))

        self.finished.emit(self.is_halted == False and successful == True)

    def change_momentum(self, stop: bool):
        self.is_halted: bool = stop

    def one_sided_image_uri(self, jsondata: dict) -> str | None:
        try:
            return jsondata['image_uris']['large']
        except (KeyError, IndexError):
            return ''
        except TypeError:
            return None

    def side_image_uri(self, jsondata: dict, num: int) -> str | None:
        try:
            return jsondata['card_faces'][num]['image_uris']['large']
        except (KeyError, IndexError):
            return ''
        except TypeError:
            return None

    def first_side_image_uri(self, jsondata: dict) -> str | None:
        return self.side_image_uri(jsondata, num=0)

    def second_side_image_uri(self, jsondata: dict) -> str | None:
        return self.side_image_uri(jsondata, num=1)

    def decode_json(self, fakefile: io.BytesIO) -> dict | None:
        fakefile.seek(0)
        data = fakefile.read()
        try:
            jsondata: dict = json.loads(data)
            return jsondata
        except json.JSONDecodeError:
            print(f'error decoding JSON for {get_expname(self.card_data)} - {self.card_data[Card.name]}')
            return None

    def basic_downloading(self, url: str, timeout: float = 5.0) -> io.BytesIO | None:
        if self.is_halted:
            return None

        fakefile = io.BytesIO()
        eof: bool = False
        try:
            start_time: float = time.time()
            if os.name in 'posix':
                kwgs = dict(url=url)
            else:
                ctx = ssl.create_default_context(cafile=certifi.where())
                kwgs = dict(url=url, context=ctx)

            with urllib.request.urlopen(**kwgs) as plow:
                while not eof and time.time() < (start_time + timeout) and not self.is_halted:
                    chunk: bytes = plow.read(8192)
                    eof: bool = chunk == b''
                    fakefile.write(chunk) if not eof else ...
        finally:
            return fakefile if eof else None


    def get_base_url(self) -> str:
        return f'https://api.scryfall.com/cards/{self.card_data[Card.scryfall_id]}'

    def start_scryfall_downloading(self) -> bool | None:
        card_data: tuple = self.card_data
        path: str = webp_path(card_data)
        if os.path.exists(path):
            return True
        else:
            self.lock.acquire(timeout=30)
            if self.is_halted: # could become halted during aquire (singleton race)
                if self.lock.locked():
                    self.lock.release()
                return None

        base_url: str = self.get_base_url()
        fakefile: io.BytesIO | None = self.basic_downloading(url=base_url)
        jsondata: dict | None = self.decode_json(fakefile) if fakefile is not None else None
        if not jsondata:
            text: str = f'couldnt download details for {get_setcode(card_data)} - {card_data[Card.name]}'
            self.errors.append(text)
        else:
            if not card_data[Card.side]:
                image_uri: str | None = self.one_sided_image_uri(jsondata) or self.first_side_image_uri(jsondata)
            else:
                if card_data[Card.side] == 'a':
                    image_uri: str | None = self.first_side_image_uri(jsondata) or self.one_sided_image_uri(
                        jsondata)
                else:
                    image_uri: str | None = self.second_side_image_uri(jsondata) or self.one_sided_image_uri(
                        jsondata)

            if image_uri is None:
                text: str = f'couldnt download details for {get_setcode(card_data)} - {card_data[Card.name]}'
                self.errors.append(text)
            elif image_uri == "":
                text: str = (
                    f'cannot locate image_uri for {get_setcode(card_data)} - {card_data[Card.name]}\n'
                    f'JSON-data: {jsondata}'
                )
                self.errors.append(text)
            else:
                fakefile: io.BytesIO | None = self.basic_downloading(url=image_uri)
                im = None
                try:
                    fakefile.seek(0)
                    im = Image.open(fakefile)
                    im.save(path, format='webp', method=6, quality=80)
                except FileNotFoundError:
                    subdir: str = get_subdir(card_data)
                    try:
                        pathlib.Path(subdir).mkdir(exist_ok=True, parents=True)
                        im = Image.open(fakefile)
                        im.save(path, format='webp', method=6, quality=80)
                    except PermissionError:
                        text: str = f'cannot create {subdir} !!!'
                        self.errors.append(text)

                except AttributeError:
                    text: str = f'couldnt download "large" image for {get_setcode(card_data)} - {card_data[Card.name]}'
                    self.errors.append(text)

                finally:
                    if not self.errors and not self.is_halted and im is not None:
                        sync_sec: float = 1.0
                        while not os.path.exists(path) and sync_sec > 0.0:
                            time.sleep(0.1)
                            sync_sec -= 0.1
                            try:
                                os.sync()
                            except OSError:
                                ...
                        if os.path.exists(path):
                            print(
                                f'[\33[38:5:249mDOWNLOADED\33[0m] '
                                f'{get_expname(card_data)}: {card_data[Card.name]} '
                                f'[\33[38:5:249mWEBP {im.width} x {im.height} -> '
                                f'\33[33:1:15m{os.path.getsize(path) // 1000}\33[0m kb]'
                            )

        if self.lock.locked():
            self.lock.release()

        return None if (self.is_halted or self.errors) else os.path.exists(path)

LOCK: Lock = Lock()

class CardImageLocation:
    def __init__(self, db_input: tuple):
        self.thread: None | QtCore.QThread = None
        self.worker: None | Worker = None
        self.__call__(db_input)

    def __call__(self, db_input: tuple):
        self.successful_download: None | bool = None
        self.db_input = db_input
        self.full_path: str = webp_path(db_input)
        self.image_existed: bool = os.path.exists(self.full_path)

    def __bool__(self) -> bool:
        return self.image_existed or os.path.exists(self.full_path)

    def __repr__(self) -> str:
        return self.full_path

    def stop_download(self):
        if self.worker and self.successful_download is None:
            self.worker.stop_downloading.emit(True)

        self.kill_thread()

    def kill_thread(self):
        if self.thread:
            try:
                self.thread.quit()
                self.thread.wait()
            finally:
                self.thread = None
                self.worker = None

    def download_image(self, finished_fn = None):
        if self.successful_download is not None: # retry denied
            return

        self.kill_thread()

        self.thread = QtCore.QThread()
        self.worker = Worker(self.db_input, lock=LOCK)
        self.worker.moveToThread(self.thread)

        if finished_fn is not None:
            self.worker.finished.connect(finished_fn)

        self.worker.finished.connect(self.download_finished)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def download_finished(self, successful_download: bool):
        self.successful_download = successful_download
        self.kill_thread()

        # print(f'downloading was not successful!' if not successful_download else f'downloading was successful!')
