# coding: utf-8
# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.0 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Bram Cohen
'''
@note: 
速度测量器。定义于BitTorrent/RateMeasure.py中，和Measure不一样的地方在于
它可以在初始化的时候传入一个表示还剩多少字节的参数进去，因而它多了一个功能，那就是
根据当前的速率，估算出预计剩余时间。_SingleTorrent中定义了一个RateMeasure。 
'''

from time import time


class RateMeasure(object):

    def __init__(self, left):
        self.start = None
        self.last = None
        self.rate = 0
        self.remaining = None
        self.left = left
        self.broke = False
        self.got_anything = False

    def data_came_in(self, amount):
        if not self.got_anything:
            self.got_anything = True
            self.start = time() - 2
            self.last = self.start
            self.left -= amount
            return
        self.update(time(), amount)

    def data_rejected(self, amount):
        self.left += amount

    def get_time_left(self):
        if not self.got_anything:
            return None
        t = time()
        if t - self.last > 15:
            self.update(t, 0)
        return self.remaining

    def get_size_left(self):
        return self.left

    def update(self, t, amount):
        self.left -= amount
        try:
            self.rate = ((self.rate * (self.last - self.start)) + amount) / (t - self.start)
            self.last = t
            self.remaining = self.left / self.rate
            if self.start < self.last - self.remaining:
                self.start = self.last - self.remaining
        except ZeroDivisionError:
            self.remaining = None
        if self.broke and self.last - self.start < 20:
            self.start = self.last - 20
        if self.last - self.start > 20:
            self.broke = True
