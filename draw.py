from PIL import ImageOps
from PIL.Image import Image
from PIL.ImageDraw import ImageDraw

from draw_arrows import Direction, CoordinateArrow

RED = (255, 0, 0)
BLACK = (0, 0, 0)

SAFE_MARGIN = 200
MARGIN = 10
DISTANCE = 5  # Distance for found pixel near element


class Draw:

    def __init__(self, coords, image: Image):
        self.coords = coords
        self.image = image
        self.image_w, self.image_h = image.size
        self.arrow = CoordinateArrow().get_arrow_coordinate

    def draw(self):
        """
        Draws a line with correction for free space near element.
        """
        (x1, y1, x2, y2) = self.coords
        color = self._get_color_contour()
        print(self)
        coords, direction = self._check_free_space()

        draw = ImageDraw(self.image)
        draw.rectangle(((x1, y1), (x2, y2)), outline=color, width=4)

        if coords is not None:
            arrow = self.arrow(coords, 150, 50, 10, direction)
            for line in arrow:
                draw.line(line, fill=color, width=4)
        del draw
        image = ImageOps.expand(self.image, border=3, fill=BLACK)
        return image

    def _get_color_contour(self):
        """
        Changes the color of the outline depending on the environment of the element.
        """
        (x1, y1, x2, y2) = self.coords
        image = self.image.convert("RGB")
        for pixel in [(x1 - DISTANCE, y1), (x1, y1 - DISTANCE), (x2 + DISTANCE, y2), (x2, y2 + DISTANCE)]:
            if not all([p >= 0 for p in pixel]) or not pixel[0] <= self.image_w or not pixel[1] <= self.image_h:
                continue
            elif self._check_color_range(image.getpixel(pixel)):
                return BLACK
        return RED

    @staticmethod
    def _check_color_range(color):
        min_range_color = 150
        max_range_color = 255
        return min_range_color <= color[0] <= max_range_color and \
               (0 <= color[1] <= min_range_color or 0 <= color[2] <= min_range_color)

    def _check_free_space(self):
        """
        Searches for free space near an item, for drawing arrow.
        """
        (x1, y1, x2, y2) = self.coords

        left, right = SAFE_MARGIN, self.image_w - SAFE_MARGIN
        top, bottom = SAFE_MARGIN, self.image_h - SAFE_MARGIN

        if x1 >= left and y2 <= bottom:
            return (x1 - MARGIN, y2 + MARGIN), Direction.BOTTOM_LEFT
        elif x2 <= right and y1 >= top:
            return (x2 + MARGIN, y1 - MARGIN), Direction.TOP_RIGHT
        elif x1 >= left and y1 >= top:
            return (x1 - MARGIN, y1 - MARGIN), Direction.TOP_LEFT
        elif x2 <= right and y2 <= bottom:
            return (x2 + MARGIN, y2 + MARGIN), Direction.BOTTOM_RIGHT
        elif x1 >= left and not (y1 >= top and y2 <= bottom):
            return (x1 - MARGIN, (y1 + y2) / 2), Direction.LEFT
        elif not x1 >= left and y1 >= top:
            return ((x1 + x2) / 2, y1 - MARGIN), Direction.TOP
        elif x2 <= right and not (y1 >= top and y2 <= bottom):
            return (x2 + MARGIN, (y1 + y2) / 2), Direction.RIGHT
        elif not x2 <= right and y2 <= bottom:
            return ((x1 + x2) / 2, y2 + MARGIN), Direction.BOTTOM
        return None, None