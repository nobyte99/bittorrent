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
BitTorrent/makemetafile.py模块中提供函数make_meta_files。它的参数意义如下： 

    URL：Tracker的URL地址，在BT的协议设计中，还是需要有个服务器作为tracker来协调各个客户端的下载的，tracker部分的程序以后会介绍，现在只需要知道这个URL将要作为一条信息写入到种子文件中即可。 

    file：种子文件的来源文件或目录列表(即准备要在BT上共享的资源)，注意，这里的列表意思是该列表中的每一项都为其生成一个种子文件，而此列表中的每一项可以是一个文件或者是一个目录。 

    flag：一个Event对象，可以用来检查是否用户要求中止程序。程序设计得比较合理，可以在很细的粒度下检查这个Event是否被触发，如果是则中止执行。 

    progressfunc：一个回调函数，程序会在恰当的地方调用它，以表示现在的工作进度，在命令行模式下，这个回调函数被指向在控制台上显示进度信息的函数，在GUI模式下，这个回调函数则会影响一个图形界面的进度条。 

    filefunc：也是一个回调函数，程序会在恰当的地方调用它，以表示现在在处理哪个文件。 

    piece_len_pow2：分块的大小，BT中把要共享的资源分成固定大小的块，以便处理。这个参数就是用2的指数表示的块的大小，例如当该参数为19的情况下，则表示共享的资源将被分成512k大小的块为单位进行处理。 

    target：目标文件地址，即种子文件的地址。这个参数可以不指定(None)，则种子文件将与公享资源处于同一目录。 

    comment：说明。一段可以附加在种子文件内的信息。 

    filesystem_encoding：文件系统编码信息。 

    make_meta_files的主要工作是进行一系列的检查。例如在开始的时候就检查files的长度(
    元素的个数)和target，当files的长度大于1且target不是None的时候就会报错，
    因为如果要生成多个种子文件的话，是不能指定target的(这样target只确定了一个种子文件
    的保存位置)。接下来检查文件系统的编码问题。然后把files中所有以.torrent结尾的项目全
    部刨掉，剩下的作为参数传递给 make_meta_file进行处理，注意，这个函数一次生成一个种子文件。 
'''
from __future__ import division

import os
import sys
from sha import sha
from time import time
from threading import Event

from BitTorrent.bencode import bencode
from BitTorrent.btformats import check_info
from BitTorrent.parseargs import parseargs, printHelp
from BitTorrent.obsoletepythonsupport import *
from BitTorrent import BTFailure

ignore = ['core', 'CVS', 'Thumbs.db']

def dummy(v):
    pass

def make_meta_files(url, files, flag=Event(), progressfunc=dummy,
                    filefunc=dummy, piece_len_pow2=None, target=None,
                    comment=None, filesystem_encoding=None):
    if len(files) > 1 and target:
        raise BTFailure("You can't specify the name of the .torrent file when "
                        "generating multiple torrents at once")

    if not filesystem_encoding:
        try:
            sys.getfilesystemencoding
        except AttributeError:
            pass
        else:
            filesystem_encoding = sys.getfilesystemencoding()
        if not filesystem_encoding:
            filesystem_encoding = 'ascii'
    try:
        'a1'.decode(filesystem_encoding)
    except:
        raise BTFailure('Filesystem encoding "'+filesystem_encoding+
                        '" is not supported in this version')
    files.sort()
    ext = '.torrent'

    togen = []
    for f in files:
        if not f.endswith(ext):
            togen.append(f)

    total = 0
    for f in togen:
        total += calcsize(f)

    subtotal = [0]
    def callback(x):
        subtotal[0] += x
        progressfunc(subtotal[0] / total)
    for f in togen:
        if flag.isSet():
            break
        t = os.path.split(f)
        if t[1] == '':
            f = t[0]
        filefunc(f)
        make_meta_file(f, url, flag=flag, progress=callback,
                       piece_len_exp=piece_len_pow2, target=target,
                       comment=comment, encoding=filesystem_encoding)

def make_meta_file(path, url, piece_len_exp, flag=Event(), progress=dummy,
                   comment=None, target=None, encoding='ascii'):
    piece_length = 2 ** piece_len_exp
    a, b = os.path.split(path)
    if not target:
        if b == '':
            f = a + '.torrent'
        else:
            f = os.path.join(a, b + '.torrent')
    else:
        f = target
    info = makeinfo(path, piece_length, flag, progress, encoding)
    if flag.isSet():
        return
    check_info(info)
    h = file(f, 'wb')
    data = {'info': info, 'announce': url.strip(),'creation date': int(time())}
    if comment:
        data['comment'] = comment
    h.write(bencode(data))
    h.close()

def calcsize(path):
    total = 0
    for s in subfiles(os.path.abspath(path)):
        total += os.path.getsize(s[1])
    return total

def makeinfo(path, piece_length, flag, progress, encoding):
    def to_utf8(name):
        try:
            name = name.decode(encoding)
        except Exception, e:
            raise BTFailure('Could not convert file/directory name "'+name+
                            '" to utf-8 ('+str(e)+'). Either the assumed '
                            'filesystem encoding "'+encoding+'" is wrong or '
                            'the filename contains illegal bytes.')
        return name.encode('utf-8')
    path = os.path.abspath(path)
    if os.path.isdir(path):
        subs = subfiles(path)
        subs.sort()
        pieces = []
        sh = sha()
        done = 0
        fs = []
        totalsize = 0.0
        totalhashed = 0
        for p, f in subs:
            totalsize += os.path.getsize(f)

        for p, f in subs:
            pos = 0
            size = os.path.getsize(f)
            p2 = [to_utf8(name) for name in p]
            fs.append({'length': size, 'path': p2})
            h = file(f, 'rb')
            while pos < size:
                a = min(size - pos, piece_length - done)
                sh.update(h.read(a))
                if flag.isSet():
                    return
                done += a
                pos += a
                totalhashed += a

                if done == piece_length:
                    pieces.append(sh.digest())
                    done = 0
                    sh = sha()
                progress(a)
            h.close()
        if done > 0:
            pieces.append(sh.digest())
        return {'pieces': ''.join(pieces),
            'piece length': piece_length, 'files': fs,
            'name': to_utf8(os.path.split(path)[1])}
    else:
        size = os.path.getsize(path)
        pieces = []
        p = 0
        h = file(path, 'rb')
        while p < size:
            x = h.read(min(piece_length, size - p))
            if flag.isSet():
                return
            pieces.append(sha(x).digest())
            p += piece_length
            if p > size:
                p = size
            progress(min(piece_length, size - p))
        h.close()
        return {'pieces': ''.join(pieces),
            'piece length': piece_length, 'length': size,
            'name': to_utf8(os.path.split(path)[1])}

def subfiles(d):
    r = []
    stack = [([], d)]
    while stack:
        p, n = stack.pop()
        if os.path.isdir(n):
            for s in os.listdir(n):
                if s not in ignore and not s.startswith('.'):
                    stack.append((p + [s], os.path.join(n, s)))
        else:
            r.append((p, n))
    return r
