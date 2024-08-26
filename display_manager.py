#-------------------------------------------------------------------------------
# Name:        Display Manager
# Purpose:
#
# Author:      Dave
#
# Created:     12/03/2014
# Copyright:   (c) Dave 2014
# Licence:     <your licence>
#-------------------------------------------------------------------------------
"""
This module encapsulates all functions related to the display of
user messages on the LCD  and to the control of the piezo buzzer.
It provides a programming  interface for setting the text messages that are
displayed on the individual lines of the LCD and to set the display mode,
such as scrolling, of each line.  This module also implements the display timer
and provides an interface to start the timer for a specified number of seconds
and generates the associated timer expired event.

FSM Control Events

E9:Display Timer Expired
This event signals that the Display Timer has expired.
The Display Timer is a timer set to expire in a pre-determined amount of time
and enables the user to have an opportunity to view display messages for the
pre-determined time, before the timer expires.  This event is useful to
enable the automatic transition to a new state upon expiration of the timer.


"""


def main():
    pass

if __name__ == '__main__':
    main()


import threading
import time


# importing with format 'from module import name' allows
# direct use of the object name in the code
# rather than having to use module.object if just import module is used
# this willmake for cleaner code when used below


#import logger object from config file
from kk_logger import kklog

# import the fsm event queue
from config import fsm_event_queue
# import the fsm error queue
from config import fsm_error_queue

# import the KK fsm event defintions required for this module
from config import e_display_timer_expire

# import function to look up configruation key=value values
# from the configuration data dictionary
from config import GetConfigurationValue

# this module executes a thread so import the thread run control flag
# from config import thread_run_flag
from config import GetThreadRunFlag

# import function to see what mode to use:emulation or actual BBB hardware
from config import RunBBBHW

# import amount of time to display messages
from config import DISPLAY_TIMER

# use the hardware emulator for testing
import kk_hw_emulator

# if running with actual Beaglebone hardware import the HW libs
if RunBBBHW():
    #import Adafruit_BBIO.GPIO as GPIO
    #import Adafruit_BBIO.PWM as PWM

    #RPi IO library
    import RPi.GPIO as GPIO
    #GPIO.setmode(GPIO.BOARD)
    #GPIO.cleanup()



# create an event to signal when there is a new set of
# messages to display
NewMessageEvent = threading.Event()

# create a global display message list and a lock to protect it
# this allows a syncronous interface between the function that sets
#the display message list and the thread that reads it for display
# on the LCD hardware
global_display_list = []
DisplayListLock = threading.Lock()

# function to set the global message list
def SetDisplayList(lcd_messages):
    global global_display_list
    with DisplayListLock:
        global_display_list = []
        for msg in lcd_messages:
            #print("SetDisplayList: " + msg)
            global_display_list.append(msg)
    NewMessageEvent.set()


# function to get the global message list
def GetDisplayList(lcd_messages):
    global global_display_list
    with DisplayListLock:
        #lcd_messages = []
        for msg in global_display_list:
            lcd_messages.append(msg)


# temporarily insert a message into the display stream and
# then resort back to the message that was displayed previously
# this allows a transient message to displayed without overwriting messages
# being displayed by the FSM state machine
def InsertTempDisplayMessage(temp_display_messages):
    # save the current list of messages that are being saved
    cur_lcdmessages = []
    lcd_messages = []
    GetDisplayList(cur_lcdmessages)
    # update the display with the temporary message and then
    # sleep for for twice the current message display time: this insures the temp message is displayed for some time
    UpdateDisplay(temp_display_messages)
    time.sleep(DISPLAY_TIMER*2)
    # restore the saved current message  list
    # only if the active display list matches the temp messsage
    # the two could now be different if some other thread had updated the display durring the sleep time
    GetDisplayList(lcd_messages)
    if(temp_display_messages == lcd_messages):
        UpdateDisplay(cur_lcdmessages)

# display update function
def UpdateDisplay(display_messages):
    result = True

    # expand all symbolic place holders in the messages to be displayed
    msgidx = 0
    lcd_messages = []
    for lcdmsg in display_messages:
        lcd_messages.append(ReplaceMessageSymbols(lcdmsg))
        ++msgidx

    # set the message list for access by the LCD display thread
    SetDisplayList(lcd_messages)

    if RunBBBHW():
        # update the LCD message
        #pseudo code: LCDHardwareSetMessage(line_numer,lcdmsg)
        pass
    # use the hw emulator
    emulatormessage = "LCD0:"
    for lcdmsg in lcd_messages:
        emulatormessage += lcdmsg + " : "
    kk_hw_emulator.lcdmessage1 = emulatormessage



# this function formats the display messages by expanding out any symbolic
# tokens embeded within the message
def ReplaceMessageSymbols(input_message):
    retmsg = input_message
    # if error msg symbol then read actual errors messages off of error queue
    if ( input_message == "<errorqueue>"):
        try:
            retmsg=''
            msgseperator = ' '
            while True:
                qmsg = fsm_error_queue.popleft()
                retmsg += qmsg + msgseperator
                msgseperator = '-'
        except IndexError:
        # nothing on queue , so just continue to loop
            pass
        # remove trailing message seperator
        retmsg = retmsg.rstrip('-')
    # if not an error msg symbol then do any required parameter substitution
    else:
        msgwords = retmsg.split()
        for word in msgwords:
            # key values in the message that are to be replaced are delimited as <key>
            if(word.find('<') == 0):
               configval = GetConfigurationValue(word)
               retmsg = retmsg.replace(word,configval)

    # return formatted message
    return(retmsg)

#display timer function
def RunDisplayTimer():
    # set the time timeout time.
    time.sleep(DISPLAY_TIMER)
    #print "display timer expire"
    fsm_event_queue.append(e_display_timer_expire)


# function to output an audio signal
from config import AUDIO_PIN
def AudioSignal():
    # running on BBB Hardware then use it's audio output
    if RunBBBHW():
        try:
            #use the BBB PWM output
            # to drive the piezo element
            #PWM.start(channel, duty, freq=2000, polarity=0)
            #PWM.start(AUDIO_PIN,50,1566) # C6 = 1074 G5=783
            #time.sleep(.3)
            #PWM.stop(AUDIO_PIN)
            GPIO.setup(AUDIO_PIN, GPIO.OUT)
            p = GPIO.PWM(AUDIO_PIN,1566)
            p.ChangeDutyCycle(50)
            p.start(1)
            time.sleep(.3)
            p.stop()
        except ImportError:
            pass
    else:
        # no using hardware so try to
        # emulate the piezo buzzer
        # by using the windows audio library instead
        try:
            import winsound
            Freq = 2500 # Set Frequency To 2500 Hertz
            Dur = 500 # Set Duration To 1000 ms == 1 second
            winsound.Beep(Freq,Dur)
        except ImportError:
        # no windows sound module
            pass


# All code below is for interfacing display messages with an HD44780 LCD
# The wiring for the LCD is as follows:
# 1 : GND
# 2 : 5V
# 3 : Contrast (0-5V)*
# 4 : RS (Register Select)
# 5 : R/W (Read Write)       - GROUND THIS PIN
# 6 : Enable or Strobe
# 7 : Data Bit 0             - NOT USED
# 8 : Data Bit 1             - NOT USED
# 9 : Data Bit 2             - NOT USED
# 10: Data Bit 3             - NOT USED
# 11: Data Bit 4
# 12: Data Bit 5
# 13: Data Bit 6
# 14: Data Bit 7
# 15: LCD Backlight +5V**
# 16: LCD Backlight GND

#import the GPIO pin mappings
from config import LCD_RS
from config import LCD_E
from config import LCD_D4
from config import LCD_D5
from config import LCD_D6
from config import LCD_D7


# if using actual hardware then define constants
if RunBBBHW():
    LCD_CHR = GPIO.HIGH
    LCD_CMD = GPIO.LOW

# Define some device constants
LCD_WIDTH = 16    # Maximum characters per line
LCD_LINE_1 = 0x80 # LCD RAM address for the 1st line
LCD_LINE_2 = 0xC0 # LCD RAM address for the 2nd line
# Timing constants
E_PULSE = 0.0007
E_DELAY = 0.0007
# time to display a message before scolling horizontally to the next message
# in the message display list
LCD_SCROLL_TIME = 1.75


# create a thread class to aysnchrounously write messages to the LCD display
class WriteLCD(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        # if using actual hardware then intialize it
        if RunBBBHW():
            # setup LCD output Pins on BBB
            GPIO.setup(LCD_E, GPIO.OUT)  # E
            GPIO.setup(LCD_RS, GPIO.OUT) # RS
            GPIO.setup(LCD_D4, GPIO.OUT) # DB4
            GPIO.setup(LCD_D5, GPIO.OUT) # DB5
            GPIO.setup(LCD_D6, GPIO.OUT) # DB6
            GPIO.setup(LCD_D7, GPIO.OUT) # DB7
            # now send commands to setup and initialze the physical display
            lcd_init()

    def run(self):
        kklog.append( "running LCD write thread")


        while GetThreadRunFlag():
            # get the list of new messages to display on the lcd
            # these new messages are set asynchrounously by other threads and
            # retrieved via the GetDisplayList function which retruns a local copy of the
            # message list in the lcdmessages array
            lcdmessages = []
            GetDisplayList(lcdmessages)
            #print lcdmessages
            if len(lcdmessages) > 0 :
                scrollmessages = True
            else:
                scrollmessages = False
                time.sleep(.1)


            # continue scrolling the current messages until
            # there are new ones to update
            while scrollmessages & GetThreadRunFlag() :
                #DMS 04042018
                # reinit the display everytime there are new messages to display
                # this is to TRY to correct a condition where the physical LCD is
                # getting corrupted and displaying Garbage;
                lcd_init()
                for message in lcdmessages:
                    #print "next scroll message: "+ message
                    lcd_write_message(message)
                    # see if there are new messages to display
                    # by waiting for a LCD_SCROLL_TIME second time out, the display
                    # will be cycled with the current messages in the lcdmessages array every LCD_SCROLL_TIME seconds
                    # until new messages are available
                    NewMessageEvent.wait(LCD_SCROLL_TIME)
                    if NewMessageEvent.isSet():
                        #there are new messages to be displayed so jump out of displaying the current lcd messages
                        NewMessageEvent.clear()
                        # new messags are available
                        # break out of scroll loop and get them
                        scrollmessages = False
                        break

        kklog.append( "Exiting LCD display thread")




# function to format and write a message to the LCD
def lcd_write_message(message):

    # break the message up into two lines if needed
    #
    # if the message is longer than the width of an LCD line (16 chars)
    # then split it so it will be displayed on two lines.
    # te first line will be broken at LCD_Width chars or less and
    # the remainder will be displayed on the second line
    #
    # get all the words in the message into an array
    msgwords = message.split()
    # see where the position of each word is in the line
    # if a given word crosses the LCD_Width postion
    # then slpit the line right before the word starts
    msgline1 = message
    msgline2 = ''
    for word in msgwords :
        #print(word)
        idx = message.find(word)
        #print(idx)
        #print(idx + len(word) )
        if( (idx + len(word) ) > LCD_WIDTH):
            msgline1 = message[0:idx]
            msgline2 = message[idx:]
            break
    #print msgline1 + "\n"
    #print msgline2 + "\n"

    #if using actual hardware
    if RunBBBHW():
        # send the split message to the LCD, one part on each line
        lcd_byte(LCD_LINE_1, LCD_CMD)
        lcd_string(msgline1)
        lcd_byte(LCD_LINE_2, LCD_CMD)
        lcd_string(msgline2)

# function to intialze the BBB LCD data output pins and the LCD itself
def lcd_init():

    if RunBBBHW():
      # Initialize the LCD display
      lcd_byte(0x33,LCD_CMD)
      lcd_byte(0x32,LCD_CMD)
      lcd_byte(0x28,LCD_CMD)
      lcd_byte(0x0C,LCD_CMD)
      lcd_byte(0x06,LCD_CMD)
      lcd_byte(0x01,LCD_CMD)


# function to process a character string into bytes to be sent to the LCD
def lcd_string(message):

  # fill the message out with trailing blanks up to its width
  message = message.ljust(LCD_WIDTH," ")
  # write each character in the message out as the LCD as a byte
  for i in range(LCD_WIDTH):
    lcd_byte(ord(message[i]),LCD_CHR)

# function to send a byte of data to the LCD via the BBB outpt data
# and control lines
def lcd_byte(bits, mode):
  # Send byte to data pins
  # bits = data
  # mode = True  for character
  #        GPIO.LOW for command

  GPIO.output(LCD_RS, mode) # RS

  # High bits
  GPIO.output(LCD_D4, GPIO.LOW)
  GPIO.output(LCD_D5, GPIO.LOW)
  GPIO.output(LCD_D6, GPIO.LOW)
  GPIO.output(LCD_D7, GPIO.LOW)
  if bits&0x10==0x10:
    GPIO.output(LCD_D4, GPIO.HIGH)
  if bits&0x20==0x20:
    GPIO.output(LCD_D5, GPIO.HIGH)
  if bits&0x40==0x40:
    GPIO.output(LCD_D6, GPIO.HIGH)
  if bits&0x80==0x80:
    GPIO.output(LCD_D7, GPIO.HIGH)

  # Toggle 'Enable' pin
  time.sleep(E_DELAY)
  GPIO.output(LCD_E, GPIO.HIGH)
  time.sleep(E_PULSE)
  GPIO.output(LCD_E, GPIO.LOW)
  time.sleep(E_DELAY)

  # Low bits
  GPIO.output(LCD_D4, GPIO.LOW)
  GPIO.output(LCD_D5, GPIO.LOW)
  GPIO.output(LCD_D6, GPIO.LOW)
  GPIO.output(LCD_D7, GPIO.LOW)
  if bits&0x01==0x01:
    GPIO.output(LCD_D4, GPIO.HIGH)
  if bits&0x02==0x02:
    GPIO.output(LCD_D5, GPIO.HIGH)
  if bits&0x04==0x04:
    GPIO.output(LCD_D6, GPIO.HIGH)
  if bits&0x08==0x08:
    GPIO.output(LCD_D7, GPIO.HIGH)

  # Toggle 'Enable' pin
  time.sleep(E_DELAY)
  GPIO.output(LCD_E, GPIO.HIGH)
  time.sleep(E_PULSE)
  GPIO.output(LCD_E, GPIO.LOW)
  time.sleep(E_DELAY)



