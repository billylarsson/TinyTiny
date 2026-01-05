from PIL             import Image
from PIL.ImageDraw   import ImageDraw
from PIL.ImageQt     import ImageQt
from PyQt6           import QtCore, QtGui
from ui.basics       import Label, MoveLabel
from useful.database import Card
from useful.images   import CardImageLocation
from useful.tech     import add, add_rgb, shrinking_rect, sub, sub_rgb

class DragNDrop(MoveLabel):

    def __init__(self, main, source, card_data: tuple, **kwargs):
        self.source = source
        self.card_data: tuple = card_data
        super().__init__(main, **kwargs)
        self.image_label = Label(self)
        self.background = Label(self)
        self.img_loc: CardImageLocation = CardImageLocation(self.card_data)

    def resizeEvent(self, a0):
        [obj.resize(self.width(), self.height()) for obj in (self.background, self.image_label)]

        args: tuple = 'RGBA', (self.background.width(), self.background.height()), (0, 0, 0, 0)
        im = Image.new(*args)
        draw = ImageDraw(im)

        xy: tuple = shrinking_rect(0, *im.size)
        draw.rectangle(xy=xy, outline=(50, 50, 50, 255))

        r, g, b, a = 175, 175, 175, 255
        for n in range(1, 4):
            xy: tuple = shrinking_rect(n, *im.size)
            draw.rectangle(xy=xy, outline=(r, g, b, a))
            r, g, b = sub(r, factor=0.25), sub(g, factor=0.25), sub(b, factor=0.25)

        self.background.clear()
        qim = ImageQt(im)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.background.setPixmap(pixmap)

    def set_image(self):
        size: tuple = self.image_label.width(), self.image_label.height(),
        try:
            im = Image.open(self.img_loc.full_path)
            chop_w: int = im.width // 75
            chop_h: int = im.height // 75
            crop_args = chop_w, chop_h, (im.width - 1) - chop_w, (im.height - 1) - chop_h
            im = im.crop(crop_args)
            qim = ImageQt(im)
            pixmap = QtGui.QPixmap.fromImage(qim).scaled(*size, transformMode=QtCore.Qt.TransformationMode(1))
        except:
            self.image_label.setStyleSheet('background:black;color:transparent')
        else:
            self.image_label.clear()
            self.image_label.setPixmap(pixmap)
            if not self.image_label.hasScaledContents():
                self.image_label.setScaledContents(True)
            return True


    def drop_card(self):
        from ui.showbox import ShowBox
        from ui.commander import Commander
        overlappers: list = []
        for obj in self.parent().findChildren((ShowBox, Commander)):
            if obj != self.source and self.geometry().intersects(obj.geometry()):
                if all(string in dir(obj) for string in ['raise_time', 'insert_card_into_box']):
                    overlappers.append(obj)

        overlappers.sort(key=lambda obj: obj.raise_time, reverse=True)
        for obj in overlappers:
            obj.insert_card_into_box(self.card_data[Card.scryfall_id])
            break
