# coding: utf-8
'''
Created on 2018��5��27��

@author: xhj
'''
import unittest
import BitTorrent.bencode as bencode
import BitTorrent.bitfield as bitfield

class Test(unittest.TestCase):


    def setUp(self):
        pass


    def tearDown(self):
        pass


    # bencode 封装数据类型,主要用于封装bt种子的内容
    def testBencode(self):
        #x = list('1234554545454')  #i1234554545454e #13:1234554545454
        x = 'i1234554545454e'
        print(bencode.bdecode(x))

    # bitfield
    def testBitfield(self):
        t=bitfield.Bitfield(1000)
        print(t.array)
        print(t.tostring())
        self.assertTrue(t.array, "complete")


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()