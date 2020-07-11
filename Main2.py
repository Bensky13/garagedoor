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


class GarageDoor:
    # Number of status entries to keep
    maxStatusListLength = 5

    # List containing x number of door status (to average from to avoid false data).
    # This list has a max length of 5, new entries will shift old entries out (FIFO)
    garageDoorStatus = collections.deque(maxlen=maxStatusListLength)

    # Seconds
    pollingRate = 1

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

<<<<<<< HEAD
        sendSMSThread.join()


    def internet(host="8.8.8.8", port=53, timeout=3):
        """
        Host: 8.8.8.8 (google-public-dns-a.google.com)
        OpenPort: 53/tcp
        Service: domain (DNS/TCP)
        """
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except socket.error as ex:
            print(ex)
            return False


=======
>>>>>>> cfefed6f0c668c9ff6e9bffdfad26c0cecf174b9
    def exitHandler(self):
        print("Got an exit signal, cleaning up...")
        GPIO.cleanup()
        self.scriptRunning = False


    def doorStatusLoop(self):
        self.checkingBeamStatus = True

        while self.checkingBeamStatus or self.scriptRunning:
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
                        self.smsCounter -=1
                    time.sleep(30)
            else:
                self.smsCounter = 0
            time.sleep(1)

if __name__ == "__main__":
    garageDoorObject = GarageDoor()
