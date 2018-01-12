import subprocess
import os
import time
from datetime import datetime
from PIL import Image
from picamera import PiCamera
from picamera import Color
from io import BytesIO
from time import sleep
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

saveWidth = 1280 #width of saved picture/video
saveHeight = 720 #height of saved picture/video
senseWidth = int(saveWidth*0.10) #width of picture for comparison % of saved width
senseHeight = int(saveHeight*0.10) #height of picture for comparison % of saved height
diskSpaceToReserve = 200 * 1024 * 1024 #reserve 200MB of disk space
verbose = False
videoMode = True

cameraSettings = ['ZeroCam', 15, 90] #[exif_tags['IFDO.Artist'], framerate, rotation]
##set rotation to 270 if switch is on top of unit, 90 if on bottom##
logName = 'ZeroCamLog.txt'



threshold = 20 #how much the green channel needs to differ to count as a changed pixel
sensitivity = int((senseWidth*senseHeight)*0.05) #set how many pixels need to change 
forceCapture = True
forceCaptureTime = 20 * 60 #set force capture to once every X minutes

#capture a test image for comparison
def captureTestImage():
	camera = PiCamera()
	camera.framerate = int(cameraSettings[1])
	camera.rotation = int(cameraSettings[2])
	camera.resolution = (senseWidth, senseHeight)
	stream = BytesIO()
	if verbose:
		camera.start_preview()
	sleep(1.5)
	camera.capture(stream, format='bmp')
	stream.seek(1)
	image = Image.open(stream)
	camera.close()
	return image

#capture image to save
def saveImage(width, height, diskSpaceToReserve):
	if videoMode:
		capRange = 1
	else:
		capRange = 10
	camera = PiCamera()
	camera.exif_tags['IFDO.Artist'] = (cameraSettings[0])
	camera.framerate = int(cameraSettings[1])
	camera.rotation = int(cameraSettings[2])
	for i in range (0, capRange):
		localTime = time.asctime( time.localtime(time.time()) )
		camera.annotate_text = localTime
		localTime = time.strftime("%a-%b-%d-%G-%H-%M-%S", time.localtime(time.time()))
		if not videoMode:
			fileName = 'Picture_{0}-{1}.jpeg'.format(localTime, i+1) #use for capturing photos
		else:
			fileName = 'Video_{0}.h264'.format(localTime,) #use for capturing video
		camera.resolution = (width, height)
		with open(logName, 'a') as f:
			f.write('\n__CAPTURING \'{0}\'__'.format(fileName))
		if verbose:
			print('Capturing {0}'.format(fileName))
		if not videoMode:
			camera.capture(fileName, use_video_port = True) #use for capturing photos
		else:
			camera.start_recording(fileName)# for video
			camera.wait_recording(15)		#for video
			camera.stop_recording()			#for video
		with open(logName, 'a') as f:
			f.write('\n__Captured \'{0}\'__'.format(fileName))
		if verbose:
			print('Captured {0}'.format(fileName))
		if not videoMode:
			sleep(0.25)
	f.close()
	camera.close()

#free up disk space if needed
def keepDiskSpaceFree(bytesToReserve):
	if videoMode:
		fileExt = 'h254'
	else:
		fileExt = 'jpeg'
	if (getFreeSpace() < bytesToReserve):
		for filename in sorted(os.listdir(".")):
			if filename.startswith("capture") and filename.endswith(fileExt):
				os.remove(filename)
				with open(logName, 'a') as f:
					f.write('\n\t!!Deleted {0} to reserve disk space!!'.format(filename))
				if verbose:
					print("Deleted {0} to avoid filling disk".format(filename))
				if (getFreeSpace() > bytesToReserve):
					#f.close()
					return

#get available disk space
def getFreeSpace():
	st = os.statvfs(".")
	du = st.f_bavail * st.f_frsize
	return du

#check for differences
def motionTest(im1, im2):
	rgbChannel = 1 #0 for red, 1 for green, 2 for blue
	changedPixels = 0
	px1 = im1.load()
	px2 = im2.load()
	for x in range (0, senseWidth):
		for y in range (0, senseHeight):
			diff = abs(px1[x,y][rgbChannel]-px2[x,y][rgbChannel])
			if diff > threshold:
				changedPixels += 1
			if changedPixels >= sensitivity:
				return True #returns true if the number of changed pixels reached the sensitivity
	return False #returns false if changed pixels do not reach sensitivity

def main():
	image1 = captureTestImage() #get first image
	localTime = time.asctime(time.localtime(time.time()))
	with open(logName, 'a') as f:
		f.write('\n\n\t-!-!-ZeroCam Startup @ {0}-!-!-\n'.format(localTime))
	if verbose:
		print("capturing image1 {0}".format(localTime))
	with open(logName, 'a') as f:
		f.write('\nCapturing \"image1\" {0}'.format(localTime))
	lastCapture = int(time.time()) #set last capture time
	while True:
		#if True:
		if GPIO.input(22) == 1:
			image2 = captureTestImage() #get image for comparison
			localTime = time.asctime( time.localtime(time.time()) )
			if verbose:
				print('Capturing image2 {0}'.format(localTime))
			#with open(logName, 'a') as f:
			#	f.write('\nCapturing \"image2\" {0}'.format(localTime))
			if motionTest(image1, image2):
				with open(logName, 'a') as f:
					f.write("\n\t\t!! Motion Detected!! @ {0}".format(localTime))
				lastCapture = int(time.time())
				saveImage(saveWidth, saveHeight, diskSpaceToReserve)
				image1 = captureTestImage()
				keepDiskSpaceFree(diskSpaceToReserve)
		#force capture check
		if forceCapture:
			if ((int(time.time()) - lastCapture) > forceCaptureTime):
				localTime = time.asctime(time.localtime(time.time()))
				if verbose:
					print("Force Capture @ {0}".format(localTime))
				with open(logName, 'a') as f:
					f.write('\n\tFORCE \"image1\" CAPTURE @ {0} AFTER {1} MINUTES W\\O MOTION'.format(localTime, (forceCaptureTime/60)))
				lastCapture = int(time.time())
				image1 = captureTestImage()

try:
	if __name__ == "__main__":
		main()
except KeyboardInterrupt:
	with open(logName, 'a') as f:
		f.write('\n\nKeyboard Close\n\n')
	if verbose:
		print("Keyboard Quit")
except:
	if verbose:
		print("Unexpected Error")
	with open(logName, 'a') as f:
		f.write('\n\nUnexpected Error\n\n')
