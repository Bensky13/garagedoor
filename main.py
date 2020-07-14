import configparser
import RPi.GPIO as GPIO
import time
import atexit
import threading
import collections
import clicksend_client
from clicksend_client.rest import ApiException
import datetime


intervals = (
    ('weeks', 604800),  # 60 * 60 * 24 * 7
    ('days', 86400),    # 60 * 60 * 24
    ('hours', 3600),    # 60 * 60
    ('minutes', 60),
    ('seconds', 1),
    )

def display_time(seconds, granularity=2):
    result = []

    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append("{} {}".format(value, name))
    return ', '.join(result[:granularity])


class GarageDoor:
    # Number of status entries to keep
    maxStatusListLength = 5

    # List containing x number of door status (to average from to avoid false data).
    # This list has a max length of 5, new entries will shift old entries out (FIFO)
    garageDoorStatus = collections.deque(maxlen=maxStatusListLength)

    # Seconds
    pollingRate = 1

    # Number of polling intervals the door needs to be open, to be considered open
    minIntervals = 30

    # Status of the door right now
    currentlyOpen = None

    # Last Alert Time
    lastAlertTime = None

    # Min time between alerts (seconds)
    minAlertTime = 300

    smsConfig = None

    # If we're currently in the while loop checking the status
    checkingBeamStatus = False

    # GPIO Pimn
    BEAM_PIN = 17

    scriptRunning = True

    self.brokenCount = 0

    smsAccountAPI = False
    smsAPI = False
    notificationNumber = False



    def __init__(self):
        print("Initializing Garage Door Monitor")


        config = configparser.ConfigParser()
        config.read('settings.conf')
    
        self.setupClicksend(config)


        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.BEAM_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        #GPIO.add_event_detect(self.BEAM_PIN, GPIO.BOTH, callback=self.break_beam_callback)
        
        atexit.register(self.exitHandler)

        garageDoorStatusThread = threading.Thread(target=self.doorStatusLoop)

        garageDoorStatusThread.start()


        while self.scriptRunning:
            if self.currentlyOpen:
                if self.lastAlertTime:
                    timeDifference = (datetime.datetime.now() - self.lastAlertTime).seconds
                    if timeDifference > self.minAlertTime:
                        # Send SMS Alert
                        self.sendSMSMessage("HEY!!!! The Garage Door has been open for %s!!!" % (display_time(self.brokenCount * self.pollingRate)))

                        self.lastAlertTime = datetime.datetime.now()
                    else:
                        print("We already alerted in the last %s seconds. Not alerting again!" % timeDifference)
                else:
                    # Send SMS Alert
                    self.sendSMSMessage("HEY!!!! The Garage Door has been open for %s!!!" % (display_time(self.brokenCount * self.pollingRate)))
                    self.lastAlertTime = datetime.datetime.now()

                print("Door is currently: Open")
            else:
                print("Door is currently: Closed")
            time.sleep(1)

    def setupClicksend(config):
        if "Notifications" in config:
            if "clicksendAPI_username" in config['Notifications']:
                configuration = clicksend_client.Configuration()
                configuration.username = config['Notifications']['clicksendAPI_username']
                configuration.password = config['Notifications']['clicksendAPI_password']
                self.notificationNumber = config['Notifications']['phonenumber']
                # create an instance of the API class
                self.smsAccountAPI = clicksend_client.AccountApi(clicksend_client.ApiClient(configuration))
                try:
                    # Get account information
                    api_response = self.smsAccountAPI.account_get()
                    if "http_code': 200" not in api_response:
                        print("Invalid clicksend API response")
                        print(api_response)
                        self.smsAccountAPI = False
                    else:
                        self.smsAPI = clicksend_client.SMSApi(clicksend_client.ApiClient(configuration))

                except ApiException as e:
                    print("Exception when calling AccountApi->account_get: %s\n" % e)
                except Exception as err:
                    print("Eception when calling clicksend API")
                    print(err)

    def exitHandler(self):
        print("Got an exit signal, cleaning up...")
        GPIO.cleanup()
        self.scriptRunning = False


    def doorStatusLoop(self):
        self.checkingBeamStatus = True
        while self.checkingBeamStatus and self.scriptRunning:
            currentBeamStatus = GPIO.input(self.BEAM_PIN)
            self.brokenCount = 0

            # If currentBeamStatus is false (broken) then the door is open
            if not currentBeamStatus:
                self.brokenCount += 1
            else:
                self.brokenCount = 0
                self.currentlyOpen = False
            
            if self.brokenCount >= self.minIntervals:
                self.currentlyOpen = True
                print("Door has been open for %s seconds" % (self.brokenCount * self.pollingRate))


            time.sleep(self.pollingRate)


    def sendSMSMessage(self, message, to, retry=0):
        if to.startswith("+1"):
            try:
                message = "Garage Door Alert - %s " % message

                message = clicksend_client.SmsMessage(body=message, to=to)
                messages = clicksend_client.SmsMessageCollection(messages=[message])
                try:
                    # Send sms message(s)
                    api_response = self.smsAPI.sms_send_post(messages)
                    # print(api_response)
                except ApiException as e:
                    print("Exception when calling SMSApi->sms_send_post: %s\n" % e)
            except ConnectionResetError as err:
                print("Got an error sending SMS trying again...")
                time.sleep(1)
                if retry < 3:
                    retry += 1
                    self.sendSMSMessage(message, to, retry)
                else:
                    print("Still couldn't send that dang message. Giving up after 3 retries")

        else:
            print("Invalid phone number while trying to send message")


if __name__ == "__main__":
    garageDoorObject = GarageDoor()
