###! Using OpenCV !##
~Step 1: OpenCV3.4.6 is installed to /usr/local, proceed to step 4 if this is the preferred method. If a virtual environment is preferred, proceed to step 2.
~Step 2: To  run opencv from the python interface, first load ~/.profile to source;
$source ~/.profile
~Step 3: Then load virtual 'working' environment, either CV3 or CV4;
$workon CV3
~Step 4: load the application
$python3 application.py

##! Using Qt !##
~Step 1: Build any application like you're used to. In the case of a Qt project, run qmake first. If it's not a qt project, go to step 2.
~Step 2: run make.
~Step 3.1: if make ran succesfully, you can launch the project from the desktop using the normal execution command e.g.: "./application"
~Step 3.2: You can also run OpenGL applications (like OpenCV) from the command line interface (no desktop required), 
			run the application using the "-platform eglfs" flag e.g.L "./application -platform eglfs"

##! Installation information !##
+OS information:
~Raspbian stretch
~Linux kernel 5.1

+Install applications/packages:
~packages compiled:
	Qt 5.12.3
	QtCreator 4.8.2
	OpenCV 3.4.6 (local and virtual environment)
	OpenCV 4.1.0 (virtual environment)
~packages installed:
	PyQt5
~pip installed: 
sudo pip install \
	wheel setuptools numpy scipy matplotlib pandas scikit-learn scikit-image PyGObject ipython jupyter-core six \
	urllib3 pillow twisted cryptography protobuff tornado python-dateutil jsonschema sqlalchemy sympy more-itertools \
	websockets virtualenv-clone dlib

