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
封装了操纵系统的poll机制
到了poll对象，这是系统提供的一个提供轮询机制的模块，使用文件描述符作为参数，可以得到相应的事件
(即该文件描述符对应的插口有数据流入或者留出等)，而在这两个函数中，都调用了poll的注册函数，方
便后面的poll轮询操作。
'''
from select import select, error
from time import sleep
from types import IntType
from bisect import bisect
POLLIN = 1
POLLOUT = 2
POLLERR = 8
POLLHUP = 16


class poll(object):

    def __init__(self):
        self.rlist = []
        self.wlist = []
        
    def register(self, f, t):
        if type(f) != IntType:
            f = f.fileno()
        if (t & POLLIN) != 0:
            insert(self.rlist, f)
        else:
            remove(self.rlist, f)
        if (t & POLLOUT) != 0:
            insert(self.wlist, f)
        else:
            remove(self.wlist, f)
        
    def unregister(self, f):
        if type(f) != IntType:
            f = f.fileno()
        remove(self.rlist, f)
        remove(self.wlist, f)

    def poll(self, timeout = None):
        if self.rlist != [] or self.wlist != []:
            r, w, e = select(self.rlist, self.wlist, [], timeout)
        else:
            sleep(timeout)
            return []
        result = []
        for s in r:
            result.append((s, POLLIN))
        for s in w:
            result.append((s, POLLOUT))
        return result

def remove(list, item):
    i = bisect(list, item)
    if i > 0 and list[i-1] == item:
        del list[i-1]

def insert(list, item):
    i = bisect(list, item)
    if i == 0 or list[i-1] != item:
        list.insert(i, item)
