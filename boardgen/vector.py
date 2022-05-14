# -*- coding: utf8 -*-

"""vector.py: A simple little V class. Enabling basic vector math. """

__author__ = "Sven Hecht"
__license__ = "GPL"
__version__ = "1.0.1"
__maintainer__ = "Sven Hecht"
__email__ = "info@shdev.de"
__status__ = "Production"

from math import acos, cos, pi, sin, sqrt
from random import choice, random


class V:
    x: float
    y: float

    def __init__(self, x=0, y=0):
        self.x = 0
        self.y = 0
        if isinstance(x, tuple) or isinstance(x, list):
            y = x[1]
            x = x[0]
        elif isinstance(x, V):
            y = x.y
            x = x.x

        self.set(x, y)

    @staticmethod
    def random(size=1):
        sizex = size
        sizey = size
        if isinstance(size, tuple) or isinstance(size, list):
            sizex = size[0]
            sizey = size[1]
        elif isinstance(size, V):
            sizex = size.x
            sizey = size.y
        return V(random() * sizex, random() * sizey)

    @staticmethod
    def randomUnitCircle():
        d = random() * pi
        return V(cos(d) * choice([1, -1]), sin(d) * choice([1, -1]))

    @staticmethod
    def distance(a, b):
        return (a - b).length

    @staticmethod
    def angle(v1, v2):
        return acos(v1.dotproduct(v2) / (v1.length * v2.length))

    @staticmethod
    def angleDeg(v1, v2):
        return V.angle(v1, v2) * 180.0 / pi

    def set(self, x, y):
        self.x = x
        self.y = y

    @property
    def array(self) -> list[float]:
        return [self.x, self.y]

    @property
    def tuple(self) -> tuple[float, float]:
        return (self.x, self.y)

    @property
    def int(self) -> "V":
        return V(int(self.x), int(self.y))

    def getNormalized(self):
        if self.length != 0:
            return self / self.length
        else:
            return V(0, 0)

    def dotproduct(self, other):
        if isinstance(other, V):
            return self.x * other.x + self.y * other.y
        elif isinstance(other, tuple) or isinstance(other, list):
            return self.x * other[0] + self.y * other[1]
        else:
            return NotImplemented

    def __add__(self, other):
        if isinstance(other, V):
            return V(self.x + other.x, self.y + other.y)
        elif isinstance(other, tuple) or isinstance(other, list):
            return V(self.x + other[0], self.y + other[1])
        elif isinstance(other, int) or isinstance(other, float):
            return V(self.x + other, self.y + other)
        else:
            return NotImplemented

    def __sub__(self, other):
        if isinstance(other, V):
            return V(self.x - other.x, self.y - other.y)
        if isinstance(other, tuple) or isinstance(other, list):
            return V(self.x - other[0], self.y - other[1])
        elif isinstance(other, int) or isinstance(other, float):
            return V(self.x - other, self.y - other)
        else:
            return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, V):
            return V(other.x - self.x, other.y - self.y)
        elif isinstance(other, tuple) or isinstance(other, list):
            return V(other[0] - self.x, other[1] - self.y)
        elif isinstance(other, int) or isinstance(other, float):
            return V(other - self.x, other - self.y)
        else:
            return NotImplemented

    def __mul__(self, other):
        if isinstance(other, V):
            return V(self.x * other.x, self.y * other.y)
        elif isinstance(other, tuple) or isinstance(other, list):
            return V(self.x * other[0], self.y * other[1])
        elif isinstance(other, int) or isinstance(other, float):
            return V(self.x * other, self.y * other)
        else:
            return NotImplemented

    def __truediv__(self, other):
        if isinstance(other, V):
            return V(self.x / other.x, self.y / other.y)
        elif isinstance(other, tuple) or isinstance(other, list):
            return V(self.x / other[0], self.y / other[1])
        elif isinstance(other, int) or isinstance(other, float):
            return V(self.x / other, self.y / other)
        else:
            return NotImplemented

    def __rtruediv__(self, other):
        if isinstance(other, V):
            return V(other.x / self.x, other.y / self.y)
        elif isinstance(other, tuple) or isinstance(other, list):
            return V(other[0] / self.x, other[1] / self.y)
        elif isinstance(other, int) or isinstance(other, float):
            return V(other / self.x, other / self.y)
        else:
            return NotImplemented

    def __pow__(self, other):
        if isinstance(other, int) or isinstance(other, float):
            return V(self.x**other, self.y**other)
        else:
            return NotImplemented

    def __iadd__(self, other):
        if isinstance(other, V):
            self.x += other.x
            self.y += other.y
            return self
        elif isinstance(other, tuple) or isinstance(other, list):
            self.x += other[0]
            self.y += other[1]
            return self
        elif isinstance(other, int) or isinstance(other, float):
            self.x += other
            self.y += other
            return self
        else:
            return NotImplemented

    def __isub__(self, other):
        if isinstance(other, V):
            self.x -= other.x
            self.y -= other.y
            return self
        elif isinstance(other, tuple) or isinstance(other, list):
            self.x -= other[0]
            self.y -= other[1]
            return self
        elif isinstance(other, int) or isinstance(other, float):
            self.x -= other
            self.y -= other
            return self
        else:
            return NotImplemented

    def __imul__(self, other):
        if isinstance(other, V):
            self.x *= other.x
            self.y *= other.y
            return self
        elif isinstance(other, tuple) or isinstance(other, list):
            self.x *= other[0]
            self.y *= other[1]
            return self
        elif isinstance(other, int) or isinstance(other, float):
            self.x *= other
            self.y *= other
            return self
        else:
            return NotImplemented

    def __itruediv__(self, other):
        if isinstance(other, V):
            self.x /= other.x
            self.y /= other.y
            return self
        elif isinstance(other, tuple) or isinstance(other, list):
            self.x /= other[0]
            self.y /= other[1]
            return self
        elif isinstance(other, int) or isinstance(other, float):
            self.x /= other
            self.y /= other
            return self
        else:
            return NotImplemented

    def __ipow__(self, other):
        if isinstance(other, int) or isinstance(other, float):
            self.x **= other
            self.y **= other
            return self
        else:
            return NotImplemented

    def __eq__(self, other):
        if isinstance(other, V):
            return self.x == other.x and self.y == other.y
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, V):
            return self.x != other.x or self.y != other.y
        else:
            return NotImplemented

    def __gt__(self, other):
        if isinstance(other, V):
            return self.length > other.length
        else:
            return NotImplemented

    def __ge__(self, other):
        if isinstance(other, V):
            return self.length >= other.length
        else:
            return NotImplemented

    def __lt__(self, other):
        if isinstance(other, V):
            return self.length < other.length
        else:
            return NotImplemented

    def __le__(self, other):
        if isinstance(other, V):
            return self.length <= other.length
        else:
            return NotImplemented

    def __eq__(self, other):
        if isinstance(other, V):
            return self.x == other.x and self.y == other.y
        else:
            return NotImplemented

    def __len__(self):
        return int(sqrt(self.x**2 + self.y**2))

    @property
    def length(self):
        return sqrt(self.x**2 + self.y**2)

    def __getitem__(self, key):
        if key == "x" or key == "X" or key == 0 or key == "0":
            return self.x
        elif key == "y" or key == "Y" or key == 1 or key == "1":
            return self.y

    def __str__(self):
        return "[x: %(x)f, y: %(y)f]" % self

    def __repr__(self):
        return "{'x': %(x)f, 'y': %(y)f}" % self

    def __neg__(self):
        return V(-self.x, -self.y)

    def __bool__(self):
        return True
