# See: https://picamera.readthedocs.io/en/release-1.11/index.html
from time import sleep
from picamera import PiCamera

# Explicitly open a new file called my_image.jpg
my_file = open('my_image.png', 'wb')

# Open camera
camera = PiCamera(resolution=(3280,2464), framerate=10)

# Set ISO to the desired value
camera.iso = 200

# Wait for the automatic gain control to settle
sleep(1)

# Show parameters, perhaps fix these?
print("Exposure mode: ", camera.exposure_mode)
print("Exposure speed: ", camera.exposure_speed)
print("Shutter speed: ", camera.shutter_speed)
print("Analog gain: ", camera.analog_gain)
print("Digital gain: ", camera.digital_gain)
print("AWB mode: ", camera.awb_mode)
print("AWB gains: ", camera.awb_gains)

# capture
camera.capture(my_file, format='png')
# At this point my_file.flush() has been called, but the file has
# not yet been closed
my_file.close()

# Now fix the camera parameter values
camera.shutter_speed = camera.exposure_speed
# When queried, exposure_speed returns the shutter speed currently being used.
# The value is returned as an integer representing a number of microseconds.
# If shutter_speed is a non-zero value, then exposure_speed and shutter_speed 
# should be equal. 
camera.exposure_mode = 'off'
g = camera.awb_gains
camera.awb_mode = 'off'
camera.awb_gains = g

# Sometimes, particularly in scripts which will perform some sort of 
# analysis or processing on images, you may wish to capture smaller images 
# than the current resolution of the camera. Although such resizing can be 
# performed using libraries like PIL or OpenCV, it is considerably more 
# efficient to have the Pi’s GPU perform the resizing when capturing the image.
# This can be done with the resize parameter of the capture() methods:
# camera.capture('my_image_resized.jpg', resize=(320, 240))
camera.capture_sequence(['image%02d.jpg' % i for i in range(10)],resize=(640,480))

# Explicitly close
camera.close()
