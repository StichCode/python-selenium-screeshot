from io import BytesIO

from PIL import Image
from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement

from draw import Draw


class Screenshot:
    """
    Class with methods for working with screenshot on page.
    """

    def __init__(self, driver: webdriver.Firefox, elements):
        self.dr = driver
        self.elements = elements
        self.images = []
        self.draw = Draw

    def get_images(self, one_size=True) -> list:
        """
        A method of obtaining a list with images of transferred elements
        indicating the boundaries of each element in the image.
        """

        self.dr.execute_script("window.scrollTo(0, 0)")
        images = []
        for element_id, element in enumerate(self.elements):

            single_image = self.single_element(element=element['element'], draw=True)

            if single_image is None:
                images.append(None)
            else:
                resize_image = self.__resize_image(single_image, one_size=one_size)
                if resize_image is not None:
                    images.append(resize_image)
                else:
                    images.append(single_image)
        return images

    def js_coords(self, el: WebElement):
        """
        Returns the coordinate element via JavaScript.
        Parameters:
            el (WebElement): Selenium element
        Returns:
            list: List with element coordinates.
        """
        c = self.dr.execute_script("return arguments[0].getClientRects();", el)  # list with client rects
        # A shorter form for checking that the dictionary is not empty
        if not c.get("0"):
            return None, None
        x, y, w, h = [c["0"]["x"], c["0"]["y"], c["0"]["width"], c["0"]["height"]]

        if w * h > 0 and el.is_displayed():
            return [x, y, x + w, y + h], None
        elif any(map(lambda i: i == 0, [w, h])):
            return self.js_coords(el.find_element_by_xpath("./parent::*"))[0], c.get("0")
        else:
            return None, None

    def single_element(self, element: Element = None, safe_area: int = None, draw: bool = False):
        """
        Returns the cropped image of the element.
        Scrolling and getting coordinates through JavaScript is used.

        Parameters:
            element (Element)
            safe_area (int): safe area around element for crop image
            draw (bool): Draws an arrow with correction for free space near element if True.
        Returns:
            Image: Cropped element image.
        """
        if element is None:
            element = self.el
        el = element.get_element(self.dr)
        self.dr.execute_script("window.scrollTo(0, 0)")

        # scroll to element
        self.dr.execute_script("arguments[0].scrollIntoView();", el)

        # get coordinates from client rect
        jsc = self.js_coords(el)
        if jsc is None:
            return None
        coords, rect = jsc
        if coords is None:
            return None

        # hide other elements to view the desired element
        if draw:
            self.hide_elements(element, coords)

        image = Image.open(BytesIO(self.dr.get_screenshot_as_png())).convert("RGBA")

        if draw and rect is not None:
            image = self.draw(coords=[rect['x'], rect['y'], rect['width'] + rect['x'], rect['height'] + rect['y']],
                              image=image).draw()
        elif draw:
            image = self.draw(coords=coords, image=image).draw()
        return self.__crop_image(image, coords, custom_safe_area=safe_area)

    def hide_elements(self, el, coords):
        """
        Hide elements like cookie for good screenshot
        """
        result = el.click(self.dr)
        if result['action'] != "NONINTERACTABLE":
            return

        elements = self.dr.execute_script(f"return document.elementsFromPoint({coords[0]}, {coords[1]})")

        for e in [el for el in elements if el.tag_name not in ["body", "html", "script"]]:
            if el not in e.find_elements_by_xpath(".//child::*") and "cookie" in e.get_attribute("outerHTML"):
                self.dr.execute_script("arguments[0].style.display = 'none';", e)

    @staticmethod
    def __resize_image(image: Image, one_size=False):
        """
        Method for resizing an image

        Used resample "BILINEAR" for better picture quality.

        :scale_percent: the percentage of the image size from the original
        :param image: image after cropping
        :return: resizing image
        """

        scale_percent = 70
        w = int(image.size[0] * scale_percent / 100)
        h = int(image.size[1] * scale_percent / 100)
        if w < 1 or h < 1:
            return None
        if one_size:
            need_w = 500
            new_h = image.size[1] / (image.size[0] / need_w)
            return image.resize((need_w, int(new_h)), resample=Image.BILINEAR)
        return image.resize((w, h))

    @staticmethod
    def __crop_image(image: Image, coords, custom_safe_area) -> Image:
        """
        image.size[0] - width screenshot
        image.size[1] - height screenshot

        max - used to define the lower boundary
        min - used to define the upper  boundary
        safe distance - a safe distance for crop the image
        :param image: image after highlighting problematic items
        :param coords: coordinates
        :return: cropped image
        """
        safe_distance = 400 if custom_safe_area is None else custom_safe_area
        (x, y, x1, y1) = coords
        return image.crop(box=(max(x - safe_distance, 0), max(y - safe_distance, 0),
                               min(x1 + safe_distance, image.size[0]), min(y1 + safe_distance, image.size[1])))

    def it_infinity(self):
        """

        """
        total = 0
        total_h = self.dr.execute_script("return document.body.scrollHeight")
        view = self.dr.execute_script("return window.innerHeight")
        while total < total_h:
            total += view
            self.dr.execute_script(f"window.scrollTo(0, {total_h})")
            total_h = self.dr.execute_script("return document.body.scrollHeight")
            if total_h > 20000:
                return True
        return False

    @classmethod
    def full_page(cls, driver: webdriver.Firefox):
        """
        Getting a picture with a screenshot of the entire page.
        """
        driver.execute_script(f"window.scrollTo({0}, {0})")
        total_width = driver.execute_script("return document.body.offsetWidth")
        total_height = driver.execute_script("return document.body.parentNode.scrollHeight")
        viewport_width = driver.execute_script("return document.body.clientWidth")
        viewport_height = driver.execute_script("return window.innerHeight")
        rectangles = []
        i = 0
        while i < total_height:
            ii = 0
            top_height = i + viewport_height
            if top_height > total_height:
                top_height = total_height
            while ii < total_width:
                top_width = ii + viewport_width
                if top_width > total_width:
                    top_width = total_width
                rectangles.append((ii, i, top_width, top_height))
                ii = ii + viewport_width
            i = i + viewport_height
        stitched_image = Image.new('RGB', (total_width, total_height))
        previous = None
        counter = 0
        for rectangle in rectangles:
            if previous is not None:
                driver.execute_script("window.scrollTo({0}, {1})".format(rectangle[0], rectangle[1]))
            file_name = f"part_{counter}.png"
            counter += 1
            driver.get_screenshot_as_file(file_name)
            screenshot = Image.open(file_name)
            if rectangle[1] + viewport_height > total_height:
                offset = (rectangle[0], total_height - viewport_height)
            else:
                offset = (rectangle[0], rectangle[1])
            stitched_image.paste(screenshot, offset)
            del screenshot
            previous = rectangle
        return stitched_image