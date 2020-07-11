import configparser
import RPi.GPIO as GPIO
import time
import atexit


class GarageDoor:
    # List containing x number of door status (to average from to avoid false data)
    garageDoorStatus = []

    # Number of status entries to keep
    maxStatusListLength = 5

    # Seconds
    pollingRate = 5

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

    def __init__(self):
        print("Initializing Garage Door Monitor")
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.BEAM_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(self.BEAM_PIN, GPIO.BOTH, callback=self.break_beam_callback)
        
        atexit.register(self.exitHandler)


        while self.scriptRunning:
            print("hey i'm just sittin here...")
            time.sleep(1)



    def exitHandler(self):
        print("Got an exit signal, cleaning up...")
        GPIO.cleanup()
        self.scriptRunning = False

    def break_beam_callback(self, channel):
        print("Got a callback!")
        if GPIO.input(self.BEAM_PIN):
            # Door Closed
            if not self.checkingBeamStatus:
                print("beam unbroken")
                self.doorStatusLoop()
            else:
                print("We're already checking the status, don't start another one.")
        else:
            # Door Open
            if not self.checkingBeamStatus:
                print("beam broken")
                self.doorStatusLoop()
            else:
                print("We're already checking the status, don't start another one.")


    def doorStatusLoop(self):
        self.checkingBeamStatus = True
        while self.checkingBeamStatus:
            print("Checking Beam Status Loop")

            currentBeamStatus = GPIO.input(self.BEAM_PIN)
            print("Current Beam Status: %s" % currentBeamStatus)
            self.garageDoorStatus.append(currentBeamStatus)

            if len(self.garageDoorStatus) >= self.maxStatusListLength:
                print("We've got 5 or more beam status entries, leaving while loop.")
                self.checkingBeamStatus = False
            else:
                time.sleep(self.pollingRate)

        print("Taking a peak at the entries in garageDoorStatus...")
        openCount = 0
        for status in self.garageDoorStatus:
            if not status:
                openCount += 1
        self.garageDoorStatus = []
        
        print("Open Count: %s" % openCount)
        if openCount >= self.maxStatusListLength / 2:
            print("Majority issssssss door is OPEN")
            self.currentlyOpen = True
        else:
            print("Majority issssssss door is CLOSED")
            self.currentlyOpen = False



if __name__ == "__main__":
    garageDoorObject = GarageDoor()
