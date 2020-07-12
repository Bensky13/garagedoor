import configparser
import RPi.GPIO as GPIO
import time
import atexit
import threading
import collections
import clicksend_client
from clicksend_client import SmsMessage
from clicksend_client.rest import ApiException
import socket
from urllib2 import urlopen


class GarageDoor:
    # Number of status entries to keep
    maxStatusListLength = 5

    # List containing x number of door status (to average from to avoid false data).
    # This list has a max length of 5, new entries will shift old entries out (FIFO)
    garageDoorStatus = collections.deque(maxlen=maxStatusListLength)

    # Seconds
    pollingRate = 60

    # Status of the door right now
    currentlyOpen = None

    # If we're currently in the while loop checking the status
    checkingBeamStatus = False

    # GPIO Pimn
    BEAM_PIN = 17
    
    #How many instances the beam is broken (door open)
    brokenCount = 0

    #Number of texts sent
    smsCounter = 0

    scriptRunning = True

    def __init__(self):
        print("Initializing Garage Door Monitor")
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.BEAM_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        #GPIO.add_event_detect(self.BEAM_PIN, GPIO.BOTH, callback=self.break_beam_callback)
        
        atexit.register(self.exitHandler)

        config = configparser.ConfigParser()
        config.read('settings.conf')


        # While there is no internet... run a continously loop.
        # THIS IS BLOCKING THE ENTIRE STATUS CHECK SCRIPT!
        noInternetCount = 0
        while not self.internet():
            print("No internet %s!!!" % noInternetCount)

            noInternetCount += 1
            time.sleep(5)

        # Configure HTTP basic authorization: BasicAuth
        username = config['Notifications']['clicksendAPI_username']
        password = config['Notifications']['clicksendAPI_password']
        notificationNumber = config['Notifications']['phonenumber']
        configuration = clicksend_client.Configuration()
        configuration.username = username
        configuration.password = password

        # create an instance of the API class
        self.api_instance = clicksend_client.SMSApi(clicksend_client.ApiClient(configuration))

        # If you want to explictly set from, add the key _from to the message.
        sms_message = SmsMessage(source="python",
                        body="Hey, the garage door has been open for five minutes.",
                        to=notificationNumber)

        self.sms_messages = clicksend_client.SmsMessageCollection(messages=[sms_message])


        garageDoorStatusThread = threading.Thread(target=self.doorStatusLoop)
        sendSMSThread = threading.Thread(target=self.sendSMS)


        garageDoorStatusThread.start()
        sendSMSThread.start()
        garageDoorStatusThread.join()

        sendSMSThread.join()

    def internet(self):
        try:
            response = urlopen('https://www.google.com/', timeout=10)
            return True
        except: 
            return False


    def exitHandler(self):
        print("Got an exit signal, cleaning up...")
        GPIO.cleanup()
        self.scriptRunning = False


    def doorStatusLoop(self):
        self.checkingBeamStatus = True
        while self.checkingBeamStatus and self.scriptRunning:
            currentBeamStatus = GPIO.input(self.BEAM_PIN)
            if currentBeamStatus == 1:
                print("Door Closed")
                self.brokenCount = 0
            else:
                print("Door Open")
                self.brokenCount += 1
                print(self.brokenCount)
            time.sleep(self.pollingRate)

            if self.brokenCount >= 5:
                self.currentlyOpen = True
                print("Hey, the door is open")
            else:
                self.currentlyOpen = False

    def sendSMS(self):
        while self.scriptRunning:
            if self.currentlyOpen == True:
                if self.smsCounter <= 5:
                    print("I'm gonna send a text")
                    try:
                        api_response = self.api_instance.sms_send_post(self.sms_messages)
                        print(api_response)
                        self.smsCounter += 1
                    except ApiException as e:
                        print("Exception when calling SMSApi->sms_send_post: %s\n" % e)
                        self.smsCounter -= 1
                    except Exception as e:
                        print("Caught global exception while sending SMS messages : %s" % e)
                        self.smsCounter -= 1
                    time.sleep(300)
            else:
                self.smsCounter = 0

if __name__ == "__main__":
    garageDoorObject = GarageDoor()
