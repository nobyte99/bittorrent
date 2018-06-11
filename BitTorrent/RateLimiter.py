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

# Written by Uoti Urpala
'''
@note: 
在Multitorrent中定义，作用是对全局的速度进行限制。由于BT通信协议中，
只有发送实际的数据会需要比较多的带宽，因而也只有在这种情况下会需要用RateLimiter来
对其进行限制。现在我们可以注意到在每个Connection中还有一个next_upload 变量，
它在其它地方都没有用到，仅仅是在这里，它的作用就是把若干个连接通过这种方式组成一个链表。
next_upload的类型是 Connection，不是Upload，这里要注意。我们看
到RateLimiter.queue函数中进行的就是数据结构中很常见的链表操作，其中 self.last指向
了上一个Connection对象，插入新的Connection对象时，last会指向它。
'''
from time import time

class RateLimiter(object):

    def __init__(self, sched):
        self.sched = sched
        self.last = None
        self.upload_rate = 1e10
        self.unitsize = 1e10
        self.offset_amount = 0

    def set_parameters(self, rate, unitsize):
        if rate == 0:
            rate = 1e10
            unitsize = 17000
        if unitsize > 17000:
            # Since data is sent to peers in a round-robin fashion, max one
            # full request at a time, setting this higher would send more data
            # to peers that use request sizes larger than standard 16 KiB.
            # 17000 instead of 16384 to allow room for metadata messages.
            unitsize = 17000
        self.upload_rate = rate * 1024
        self.unitsize = unitsize
        self.lasttime = time()
        self.offset_amount = 0

    def queue(self, conn):
        assert conn.next_upload is None
        if self.last is None:
            self.last = conn
            conn.next_upload = conn
            self.try_send(True)
        else:
            conn.next_upload = self.last.next_upload
            self.last.next_upload = conn
            self.last = conn

    def try_send(self, check_time = False):
        t = time()
        self.offset_amount -= (t - self.lasttime) * self.upload_rate
        self.lasttime = t
        if check_time:
            self.offset_amount = max(self.offset_amount, 0)
        cur = self.last.next_upload
        while self.offset_amount <= 0:
            try:
                bytes = cur.send_partial(self.unitsize)
            except KeyboardInterrupt:
                raise
            except Exception, e:
                cur.encoder.context.got_exception(e)
                bytes = 0

            self.offset_amount += bytes
            if bytes == 0 or not cur.connection.is_flushed():
                if self.last is cur:
                    self.last = None
                    cur.next_upload = None
                    break
                else:
                    self.last.next_upload = cur.next_upload
                    cur.next_upload = None
                    cur = self.last.next_upload
            else:
                self.last = cur
                cur = cur.next_upload
        else:
            self.sched(self.try_send, self.offset_amount / self.upload_rate)
