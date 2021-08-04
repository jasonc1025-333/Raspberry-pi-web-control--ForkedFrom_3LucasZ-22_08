#IMPORTS
#networking
from flask import Flask,request, render_template
from flask_socketio import SocketIO


#camera
import cv2
import base64


#motor control
import RPi.GPIO as GPIO
import smbus2 as smbus
import int_to_byte
import time


#data collection
import os
import shutil
import pathlib
import subprocess
import time


#SETUP
#app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecret'
socketio = SocketIO(app)


#camera
camera = cv2.VideoCapture(0)
time.sleep(0.5)
camera.set(3, 100)
camera.set(4, 100)
FPS = 5
canRecord = False
time.sleep(0.5)


#motor setup
PIN_I2C6_POWER_ENABLE = 17
bus = smbus.SMBus(3)
DEVICE_ADDRESS = 0x53
GPIO.setmode(GPIO.BCM)
time.sleep(0.1) #important
GPIO.setup(PIN_I2C6_POWER_ENABLE, GPIO.OUT)
time.sleep(0.1) #important
MOTOR_DEFAULT = 50
motorBias = 0


#data collection
#path names
datasetPath = os.path.join(pathlib.Path(__file__).parent.resolve(), "datasets/")
#clear all the tubs (for debugging only)
for oldTub in os.listdir(datasetPath):
    shutil.rmtree(os.path.join(datasetPath, oldTub))
tubName = "tub" + str(int(time.time())) + "/"
tubPath = os.path.join(datasetPath, tubName)
imagesPath = os.path.join(tubPath, "Images/")
biasFilePath = os.path.join(tubPath, "bias.txt")

#create the directories
os.mkdir(tubPath)
os.mkdir(imagesPath)

#open bias file and allow writing data. If file already exists it is overridden.
biasFile = open(biasFilePath, "w")


@socketio.on('startRecording')
def record():
    global canRecord
    canRecord = True
    print("Recording started")
    bus.write_i2c_block_data(DEVICE_ADDRESS,3,int_to_byte.int_to_byte_array(MOTOR_DEFAULT))
    bus.write_i2c_block_data(DEVICE_ADDRESS,4,int_to_byte.int_to_byte_array(MOTOR_DEFAULT))


@socketio.on('pauseRecording')
def stopRecord():
    global canRecord
    canRecord = False
    bus.write_i2c_block_data(DEVICE_ADDRESS,3,int_to_byte.int_to_byte_array(0))
    bus.write_i2c_block_data(DEVICE_ADDRESS,4,int_to_byte.int_to_byte_array(0))
    print("Recording paused")


@socketio.on('recordingSystem')
def recording_system():
    framesTaken = 0
    #get camera info and print it
    retval, frame = camera.read()
    height = frame.shape[0]
    width = frame.shape[1]
    channels = frame.shape[2]
    print("cam px height:", height)
    print("cam px width:", width)
    print("cam channels:", channels)
    while True:
        if canRecord:
            framesTaken += 1
            #take picture into frame
            retval, frame = camera.read()
            #flip the image horiz and vert
            frame = cv2.flip(frame, -1)
            #crop the image
            #frame = frame[height-50:height, 0:width]
            #save image into images
            cv2.imwrite(imagesPath + "frame" + str(framesTaken) + ".jpg", frame)
            #save current motor bias to bias.txt
            biasFile.write(str(motorBias) + "\n")
            #encode picture to jpg
            retval, jpg = cv2.imencode('.jpg', frame)
            #encode to base 64 string
            jpg_as_text = str(base64.b64encode(jpg))
            #remove b''
            jpg_as_text = jpg_as_text[2:-1]
            #emit text
            socketio.emit('jpg_string', jpg_as_text)
        #async sleep
        socketio.sleep(1/FPS)    
        
'''
@socketio.on('startPracticing')
def practice():
    while True:
        #take picture into frame
        retval, frame = camera.read()
        #encode picture to jpg
        retval, jpg = cv2.imencode('.jpg', frame)
        #encode to base 64 string
        jpg_as_text = str(base64.b64encode(jpg))
        #remove b''
        jpg_as_text = jpg_as_text[2:-1]
        #emit text
        socketio.emit('jpg_string', jpg_as_text)
        #async sleep
        socketio.sleep(1/FPS)
'''

@socketio.on('connect')
def connect():
    GPIO.output(PIN_I2C6_POWER_ENABLE, GPIO.HIGH)
    print('A client connected.')


@socketio.on('disconnect')
def disconnect():
    GPIO.output(PIN_I2C6_POWER_ENABLE, GPIO.LOW)
    print('A client disconnected.')


@socketio.on('motorsOn')
def motors_on():
    GPIO.output(PIN_I2C6_POWER_ENABLE, GPIO.HIGH)
    print("motor on received")


@socketio.on('motorsOff')
def motors_off():
    GPIO.output(PIN_I2C6_POWER_ENABLE, GPIO.LOW)
    print("motor off received")


@socketio.on('motorBias')
def set_motor_bias(data):
    global motorBias
    motorBias = data
    leftMotor = MOTOR_DEFAULT - motorBias
    rightMotor = MOTOR_DEFAULT + motorBias
    bus.write_i2c_block_data(DEVICE_ADDRESS,3,int_to_byte.int_to_byte_array(leftMotor))
    bus.write_i2c_block_data(DEVICE_ADDRESS,4,int_to_byte.int_to_byte_array(rightMotor))
    print("Left motor:", leftMotor)
    print("Right motor:", rightMotor)
    

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    print("Ready for clients.")
    socketio.run(app, host='0.0.0.0', port=5000)
    
print("Closing program")
#close
biasFile.close()
GPIO.cleanup()
#sanity check
print("recorded motor values: " + os.popen("wc -l < " + biasFilePath).read().strip())
print("recorded images: " + os.popen("ls " + imagesPath + " | wc -l").read().strip())