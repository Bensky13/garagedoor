from flask import Flask
from Main2 import GarageDoor

app = Flask(__name__)

door = GarageDoor()

@app.route('/')
def doorStatus():
    if door.currentlyOpen:
        return "Garage door is: Open"
    else:
        return "Garage door is: Closed"
