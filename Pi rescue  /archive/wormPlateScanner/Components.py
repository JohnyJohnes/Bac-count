#!/usr/bin/env python
import pigpio
from time import sleep
import pigpio

class PWM:
    _MAX_GPIO=32

    def __init__(self, pi, gpioarray, frequency=175):
        self.pi = pi
        
        self.frequency = frequency
        self.micros = 1000000.0 / frequency

        self.gpio = gpioarray

        self.used = [False]*self._MAX_GPIO
        self.pS = [0.0]*self._MAX_GPIO
        self.pL = [0.0]*self._MAX_GPIO
        self.old_wid = None

        self.stop = False

    def set_frequency(self, frequency):
        self.frequency = float(frequency)
        self.micros = 1000000.0 / self.frequency

    def set_cycle_time(self, micros):
        self.micros = float(micros)
        self.frequency = 1000000.0 / self.micros

    def get_frequency(self):
        return self.frequency

    def get_cycle_length(self):
        return self.micros

    def set_pulse_length_in_micros(self, gpio, length):
        length %= self.micros

        self.pL[gpio] = length / self.micros

        if not self.used[gpio]:
            self.pi.set_mode(gpio, pigpio.OUTPUT)
            self.used[gpio] = True

    def set_pulse_length_in_fraction(self, gpio, length):
        self.set_pulse_length_in_micros(gpio, self.micros * length)

    def set_pulse_start_in_micros(self, gpio, start):
        start %= self.micros
        self.pS[gpio] = start / self.micros

        if not self.used[gpio]:
            self.pi.set_mode(gpio, pigpio.OUTPUT)
            self.used[gpio] = True

    def set_pulse_start_in_fraction(self, gpio, start):
        self.set_pulse_start_in_micros(gpio, self.micros * start)

    def set_pulse_start_and_length_in_micros(self, gpio, start, length):
        self.set_pulse_start_in_micros(gpio, start)
        self.set_pulse_length_in_micros(gpio, length)

    def set_pulse_start_and_length_in_fraction(self, gpio, start, length):
        self.set_pulse_start_in_fraction(gpio, start)
        self.set_pulse_length_in_fraction(gpio, length)

    def get_GPIO_settings(self, gpio):
        if self.used[gpio]:
            return (True, self.pS[gpio], self.pL[gpio])
        else:
            return (False, 0.0, 0.0)
        
    def update(self):

      null_wave = True

      for g in range(self._MAX_GPIO):

         if self.used[g]:

            null_wave = False

            on = int(self.pS[g] * self.micros)
            length = int(self.pL[g] * self.micros)

            micros = int(self.micros)

            if length <= 0:
               self.pi.wave_add_generic([pigpio.pulse(0, 1<<g, micros)])
            elif length >= micros:
               self.pi.wave_add_generic([pigpio.pulse(1<<g, 0, micros)])
            else:
               off = (on + length) % micros
               if on < off:
                  self.pi.wave_add_generic([
                     pigpio.pulse(   0, 1<<g,           on),
                     pigpio.pulse(1<<g,    0,     off - on),
                     pigpio.pulse(   0, 1<<g, micros - off),
                     ])
               else:
                  self.pi.wave_add_generic([
                     pigpio.pulse(1<<g,    0,         off),
                     pigpio.pulse(   0, 1<<g,    on - off),
                     pigpio.pulse(1<<g,    0, micros - on),
                     ])

      if not null_wave:

         if not self.stop:

            new_wid = self.pi.wave_create()

            if self.old_wid is not None:

               self.pi.wave_send_using_mode(
                  new_wid, pigpio.WAVE_MODE_REPEAT_SYNC)

               # Spin until the new wave has started.

               while self.pi.wave_tx_at() != new_wid:

                  pass

               # It is then safe to delete the old wave.

               self.pi.wave_delete(self.old_wid)

            else:

               self.pi.wave_send_repeat(new_wid)

            self.old_wid = new_wid

    def cancel(self):
      self.stop = True
      self.pi.wave_tx_stop()

      if self.old_wid is not None:
         self.pi.wave_delete(self.old_wid)
      
      
    def deactivate(self, axis):
        for i in range(0,4):
            self.set_pulse_start_and_length_in_fraction(self.gpio[axis][i], 0, 0)
        self.update()
        
    def activate(self, axis, dir = 1, update = False):
        
        if dir is not 1:
            for i in range(3,-1,-1):
                self.set_pulse_start_and_length_in_fraction(self.gpio[axis][i], 0.75-0.25*i, .500)
        else:
            for i in range(0,4):
                self.set_pulse_start_and_length_in_fraction(self.gpio[axis][i], 0.25*i, .500)
        
        if update == True:
            self.update()

class Stopbutton:
    
    def __init__(self, pi, pin1):
        if not isinstance(pi, pigpio.pi):
            raise TypeError("Is not pigpio.pi instance.")
        pi.set_mode(pin1, pigpio.INPUT)
        self.pin1 = pin1
        self.pi = pi
        
    def read(self):
        return self.pi.read(self.pin1)
    
    
    