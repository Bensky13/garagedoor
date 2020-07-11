import configparser
import RPi.GPIO as GPIO
import time
import atexit
import threading
import collections

class GarageDoor:
    # Number of status entries to keep
    maxStatusListLength = 5

    # List containing x number of door status (to average from to avoid false data).
    # This list has a max length of 5, new entries will shift old entries out (FIFO)
    garageDoorStatus = collections.deque(maxlen=maxStatusListLength)

    # Seconds
    pollingRate = 5

    # Status of the door right now
    currentlyOpen = None

    # If we're currently in the while loop checking the status
    checkingBeamStatus = False

    # GPIO Pimn
    BEAM_PIN = 17

    scriptRunning = True

    def __init__(self):
        print("Initializing Garage Door Monitor")
        # GPIO.setmode(GPIO.BCM)
        # GPIO.setup(self.BEAM_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # GPIO.add_event_detect(self.BEAM_PIN, GPIO.BOTH, callback=self.break_beam_callback)
        
        atexit.register(self.exitHandler)

        garageDoorStatusThread = threading.Thread(target=self.doorStatusLoop)

        garageDoorStatusThread.start()


        while self.scriptRunning:
            if self.currentlyOpen:
                print("Door is currently: Open")
            else:
                print("Door is currently: Closed")
            time.sleep(1)



    def exitHandler(self):
        print("Got an exit signal, cleaning up...")
        GPIO.cleanup()
        self.scriptRunning = False


    def doorStatusLoop(self):
        self.checkingBeamStatus = True
        while self.checkingBeamStatus and self.scriptRunning:
            currentBeamStatus = GPIO.input(self.BEAM_PIN)
            print("Current Beam Status (1=Door Closed, 0=Door Open): %s" % currentBeamStatus)

            time.sleep(self.pollingRate)



if __name__ == "__main__":
    garageDoorObject = GarageDoor()
