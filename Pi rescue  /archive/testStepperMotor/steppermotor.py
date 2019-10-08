import threading
import time
import RPi.GPIO as GPIO


# todo check pull up/down , debounce and timeout settings
class StepperMotor:
    def __init__(self, pin_step, pin_direction, pin_calibration_microswitch, pin_safety_microswitch,
                 step_frequency, microswitch_bouncetime=300, calibration_timeout=20, name=""):
        """

        Args:
            pin_step: GPIO pin number for step pulse output
            pin_direction: GPIO pin number for direction output
            pin_calibration_microswitch: GPIO pin number for microswitch input in the normal direction
            pin_safety_microswitch: GPIO pin number for microswitch input in reverse direction
            step_frequency: Step frequency in steps per second
            microswitch_bouncetime: Microswitch debounce time in ms
            calibration_timeout: Calibration timeout in seconds
        """

        self.pin_step = pin_step
        self.pin_direction = pin_direction
        self.pin_calibration_microswitch = pin_calibration_microswitch  # GPIO pin for microswitch input
        self.pin_safety_microswitch = pin_safety_microswitch
        self.step_frequency = step_frequency
        self.default_step_frequency = step_frequency
        self.calibration_timeout = calibration_timeout
        self.microswitch_bouncetime = microswitch_bouncetime

        self.reversed = False  # If true then direction is reversed ie digital output HIGH
        self.microswitch_hit_event = threading.Event()  # Set when the microswitch is hit, cleared when start stepping
        self.stop_step_event = threading.Event()  # Set it to stop stepping. Clear it when start stepping.
        self.step_counter = 0  # Number of steps away from zero position

        self.name = name
        
        self.lock_step_frequency = threading.Lock()

        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        GPIO.setup(self.pin_step, GPIO.OUT, initial=GPIO.LOW)
        self.step_pwm = GPIO.PWM(self.pin_step, self.default_step_frequency)
        GPIO.setup(self.pin_direction, GPIO.OUT, initial=GPIO.LOW)

        # Setup interrupts for limit switches if used
        self.ignore_interrupt = False
        if self.pin_calibration_microswitch is not None and self.pin_safety_microswitch is not None:
            GPIO.setup(self.pin_calibration_microswitch, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.setup(self.pin_safety_microswitch, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

            # Setup microswitch interrupt
            GPIO.add_event_detect(self.pin_calibration_microswitch, GPIO.RISING, callback=self.microswitch_callback,
                                  bouncetime=self.microswitch_bouncetime)
            GPIO.add_event_detect(self.pin_safety_microswitch, GPIO.RISING, callback=self.microswitch_callback,
                                  bouncetime=self.microswitch_bouncetime)
            
    def enable_interrupts(self):
        self.ignore_interrupt = False
    
    def disable_interrupts(self):
        self.ignore_interrupt = True

    def _step(self, count=None):
        """Keep stepping until self.stop_step_event is set, or until count steps have been made if count is not None.

        Args:
            count: number of steps. If None continue stepping until stopped

        Returns:

        """
        current_step_counter = 0
        while not self.stop_step_event.is_set():
            freq = self.async_get_frequency()
            # Keep stepping until stop_step is called
            GPIO.output(self.pin_step, GPIO.HIGH)
            #time.sleep(1/(2 * freq))
            t = time.time()
            while True:
                if t - time.time() > 1/(2*freq):
                    break
                time.sleep(1/40)
            GPIO.output(self.pin_step, GPIO.LOW)
            #time.sleep(1 /(2 * freq))
            while True:
                if t - time.time() > 1/(2*freq):
                    break
                time.sleep(1/40)
            if not self.reversed:
                self.step_counter += 1
            else:
                self.step_counter -= 1
            current_step_counter += 1
            if (count is not None and current_step_counter == count) or self.microswitch_hit_event.is_set():
                self.stop_step()

    def start_step(self, count=None):
        """Start stepping"""
        self.stop_step_event.clear()
        self.microswitch_hit_event.clear()
        self.step_pwm.start(50)
        # threading.Thread(target=self._step, args=[count]).start()

    def stop_step(self):
        """Stop stepping"""
        self.stop_step_event.set()
        self.step_pwm.stop()
        self.microswitch_hit_event.clear()
        
    def async_set_frequency(self, value):
        self.step_pwm.ChangeFrequency(value)
        
        #self.lock_step_frequency.acquire()
        #self.step_frequency = value
        #self.lock_step_frequency.release()
        
    def set_duty_cycle(self, value):
        self.step_pwm.ChangeDutyCycle(value)
    
    def async_get_frequency(self):
        self.lock_step_frequency.acquire()
        value = self.step_frequency
        self.lock_step_frequency.release()
        return value        

    def reverse(self, setting=None):
        """

        Args:
            setting: set to True or False to choose a direction, if None it reversed the direction

        Returns:

        """
        if setting is not None:
            if setting:
                GPIO.output(self.pin_direction, GPIO.LOW)
            else:
                GPIO.output(self.pin_direction, GPIO.HIGH)
            self.reversed = setting
        else:
            if self.reversed:
                GPIO.output(self.pin_direction, GPIO.HIGH)
            else:
                GPIO.output(self.pin_direction, GPIO.LOW)
            self.reversed = not self.reversed

    def calibrate(self):
        """Calibrate motor to zero position.
        The motor is moved all the way to one side until the microswitch is hit."""
        # check if switch is already pressed, if so then don't move
        if GPIO.input(self.pin_calibration_microswitch) == GPIO.HIGH or GPIO.input(self.pin_safety_microswitch) == GPIO.HIGH:
            self.stop_step_event.set()
            # todo move few steps away and recalibrate
            return
        if self.pin_calibration_microswitch is not None:
            self.reverse(False)
            self.step_frequency = self.default_step_frequency
            self.start_step()
            if self.microswitch_hit_event.wait(self.calibration_timeout):
                self.step_counter = 0
                #self.microswitch_hit_event.clear()
            else:
                self.stop_step()
                messagebox.showerror('FOUT', 'Fout tijdens calibratie: Timeout (kalibreren duurt te lang)')
        else:
            messagebox.showerror('FOUT', 'Voro deze motor is geen eindschakelaar ingesteld en er kan niet worden gekalibreert')

    def microswitch_callback(self, channel):
        """Interrupt callback. This function is called when the microswitch is pressed."""
        if self.ignore_interrupt:
            return
        # Check for ghost interrupt
        time.sleep(0.01)
        if GPIO.input(self.pin_calibration_microswitch) == GPIO.HIGH or GPIO.input(self.pin_safety_microswitch) == GPIO.HIGH:
            self.microswitch_hit_event.set()
            self.stop_step()
            print("interrupt {} {}".format(self.name, channel))


class CalibrationError(BaseException):
    pass
