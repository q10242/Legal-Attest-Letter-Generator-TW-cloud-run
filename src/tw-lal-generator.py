#!/usr/bin/python
# -*- coding: utf-8 -*-
import argparse
import pdfpainter
import pdfpage
from lal_constants import *

def processArgs():
    argParser = argparse.ArgumentParser(description='台灣郵局存證信函產生器',
                                        add_help=False)
    argParser.add_argument('--help',
                            action='help',
                            help='顯示使用說明')
    argParser.add_argument('article_file',
                            action='store',
                            help='存證信函全文之純文字檔路徑')
    argParser.add_argument('--senderName',
                            action='append',
                            nargs='+',
                            metavar='寄件人姓名')
    argParser.add_argument('--senderAddr',
                            action='append',
                            metavar='寄件人詳細地址')
    argParser.add_argument('--receiverName',
                            action='append',
                            nargs='+',
                            metavar='收件人姓名')
    argParser.add_argument('--receiverAddr',
                            action='append',
                            metavar='收件人詳細地址')
    argParser.add_argument('--ccName',
                            action='append',
                            nargs='+',
                            metavar='副本收件人姓名')
    argParser.add_argument('--ccAddr',
                            action='append',
                            metavar='副本收件人詳細地址')
    return argParser.parse_args()

def readMainText():
    text_file = open(args.article_file, 'r')
    text = text_file.read()
    text_file.close()
    return text.decode('utf-8')

def fillNameAndAddress(namelist, addresslist, type):
    if namelist != None:
        for i in range(len(namelist)):
            name = namelist[0][i]
            generator.drawString(NAME_CORDINATE[type+'_x_begin'] + (i*NAME_CORDINATE[type+'_x_interval']), NAME_CORDINATE[type+'_y_begin'], name)
    if (addresslist is not None):
        generator.drawString(ADDR_CORDINATE[type+'_x_begin'] , ADDR_CORDINATE[type+'_y_begin'], addresslist[0])

def getNewLineCordinate(currentY):
    newX = CONTENT_X_BEGIN
    newY = currentY - (CONTENT_Y_INTERVAL + CONTENT_Y_FIX)
    return newX, newY

def resetCordinatesAndCounters():
    return CONTENT_X_BEGIN, CONTENT_Y_BEGIN, 1, 1

args = processArgs()
senders = args.senderName
sendersAddr = args.senderAddr
receivers = args.receiverName
receiversAddr = args.receiverAddr
cc = args.ccName
ccAddr = args.ccAddr
text = readMainText()

generator = pdfpainter.PDFPainter(GENERATED_TEXT_PATH, LETTER_FORMAT_WIDE, LETTER_FORMAT_HEIGHT)
blank_letter_producer = pdfpage.PDFPagePick(LETTER_FORMAT_PATH, GENERATED_BLANK_LETTER_PATH)

# write name and address
generator.setFont(DEFAULT_FONT_PATH, 10)
fillNameAndAddress(senders, sendersAddr, 's')
fillNameAndAddress(receivers, receiversAddr, 'r')
fillNameAndAddress(cc, ccAddr, 'c')

generator.setFont(DEFAULT_FONT_PATH, 20)
x_begin, y_begin, line_counter, word_counter = resetCordinatesAndCounters()
print 'parse content...'
for i in range(0, len(text)):
    if text[i] == '\n' or (word_counter > CONTENT_MAX_WORD_PER_LINE):
        x_begin, y_begin = getNewLineCordinate(y_begin)
        line_counter = line_counter + 1
        word_counter = 1
        if text[i] == '\n':
            continue
    if line_counter > CONTENT_MAX_LINE_PER_PAGE:
        generator.endThisPage()
        blank_letter_producer.pickIndividualPages([0])
        x_begin, y_begin, line_counter, word_counter = resetCordinatesAndCounters()
    generator.drawString(x_begin, y_begin, text[i])
    x_begin += (CONTENT_X_INTERVAL - CONTENT_X_FIX)
    word_counter = word_counter + 1
generator.endThisPage()
blank_letter_producer.pickIndividualPages([0])
blank_letter_producer.save()
generator.save()

print 'start merging...'
merger = pdfpage.PDFPageMerge(GENERATED_TEXT_PATH, GENERATED_BLANK_LETTER_PATH, GENERATED_FINAL_LETTER_PATH)
for i in range(merger.getSrcTotalPage()):
    merger.mergeSrcPageToDestPage(i, i)
merger.save()

print 'Finish. Filename: ' + GENERATED_FINAL_LETTER_PATH
