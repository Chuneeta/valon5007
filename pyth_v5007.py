"""
Simple interface between linux terminal to valon 5007
"""

import valon_synth as v
import os,sys
import serial
import serial.tools.list_ports
import struct
import time

# rf levels
rf_levels = {0: -4, 1: -1, 2: 2, 3: 5}

#==================================================
def VSerialPort():
   """
   Returns the serial port connected to the valon
 
   """
   portList = []
   for port, desc, hwid in serial.tools.list_ports.comports():
      'Port: ', port, ' Desc: ', desc, ' HwId: ', hwid

   if ( desc.find( "Valon" ) ==0 ):   # on Raspberry Pi
         portList.append( port )
   return portList[0]

#==================================================
def display_settings(synth):
   """
   Display current settings on V5007

   synth : Attribute of V5007 initialization

   """
   starttime = time.time()
   synthA_label = synth.get_label(v.SYNTH_A)
   synthB_label = synth.get_label(v.SYNTH_B)
   out_freqA = synth.get_frequency(v.SYNTH_A)
   out_freqB = synth.get_frequency(v.SYNTH_B)
   out_rflevelA = synth.get_rf_level(v.SYNTH_A)
   out_rflevelB = synth.get_rf_level(v.SYNTH_B)
   time_elapsed = round(time.time() - starttime,2)
   print 'Time Elapsed: %s seconds'%time_elapsed
   print ('******************************************************')
   print ('               VALON 5007 CONFIGURATION                ')
   print ('*******************************************************')
   print ('                 %s  %s \nFrequency (MHz):    %.1f             %.1f     \nRF Level  (dBm):      %s                %s   \n******************************************************'%(synthA_label,synthB_label,out_freqA,out_freqB,out_rflevelA,out_rflevelB))

#==================================================
def conf_settings(synth,label):
   """
   Configuring synthesizer

   synth : Attribute of V5007 initialization
   label : Synthesizer label (1 or 2)

   """
   synth_label = v.SYNTH_A if label==1 else v.SYNTH_B 
   # setting frequency
   freq = float(raw_input("Frequency in MHz of Synthesizer %s (between 137.5 and 4400): "%label))
   while ((freq<=137.5) or (freq>=4400.0)):
      print "The given frequency beyond the range of V5007. Choose a frequency between 137.5 to 4400 MHz."
      freq = float(raw_input("Frequency in MHz of Synthesizer %s (between 137.5 and 4400): "%label))
   else:
      synth.set_frequency(synth_label,freq)

   # setting RF Level
   rflevel = int(raw_input("RF Level in dBm of Synthesizer %s (-4, -1, 2, 5): "%label))
   while not (rflevel in rf_levels.values()):
      print "RF level not valid. Choose RF Level from (-4, -1, 2, 5)." 
      rflevel = int(raw_input("RF Level in dBm of Synthesizer %s (-4, -1, 2, 5): "%label))
   else:
      synth.set_rf_level(synth_label,rflevel)

#==================================================
def VCOPowerDown(label,switch=1):
   """
   Powering the synthesizer down

   label : Synthesizer label (1 or 2)
   off   : Powering Up/Down (0/1) the synthesizer

   """
   hexon = 0xBA003C
   hexoff = 0xBA083C
   conn = serial.Serial(None, 9600, serial.EIGHTBITS,serial.PARITY_NONE, serial.STOPBITS_ONE)
   port = VSerialPort()
   conn.setPort(port)
   conn.open()
   data = struct.pack('>B', 0x80 | label)
   conn.write(data)
   data=conn.read(24)
   reg0, reg1, reg2, reg3, reg4, reg5 = struct.unpack('>IIIIII', data)
   if switch==0:
      reg4=hexon
   elif switch==1:
      reg4=hexoff
   else:
      print 'Invalid input for power Up/Down, should be either 0 or 1.'
      sys.exit(0)
   data = struct.pack('>BIIIIII', 0x00 | label,reg0, reg1, reg2, reg3, reg4, reg5)
   checksum = _generate_checksum(data)
   conn.write(data + checksum)
   conn.close()

#==================================================
if __name__=='__main__':
   # opening the serial port
   port = VSerialPort()
   # connecting the synthesizer to serial port
   synth = v.Synthesizer(port)

   # display current v5007 settings
   display_settings(synth)

   chg = raw_input("Do you want to change the settings of V5007? (y/n):")
   if chg.lower() == 'y':
      chg_syn1 = raw_input("Do you want to change the settings of Synthesizer 1? (y/n): ")
      if chg_syn1.lower() == 'y':
         print ('Configuring Synthesizer 1')
         phase_lock = synth.get_pahse_lock(8)
         if phase_lock:
            powerdown = raw_input("Do you want to power down Synthesizer 1 ? (y/n): ")
            if powerdown.lower()=='y':
               VCOPowerDown(0,switch=1)
            else:
               conf_settings(synth,1)
         else:
            poweron= raw_input('Synthesizer 1 is currently powered down! Do you want to power on Synthesizer 1? (y/n):')
            if poweron.lower=='y':
               VCOPowerDown(0,switch=0)
               chg_syn1 = raw_input("Do you want to change the settings of Synthesizer 1? (y/n): ") 
               if chg_syn1.lower() == 'y':
                  conf_settings(synth,1)

      chg_syn2 = raw_input("Do you want to change the settings of Synthesizer 2 ? (y/n): ")
      if chg_syn2.lower() == 'y':
         print ('Configuring Synthesizer 2')
         phase_lock = synth.get_pahse_lock(0)
         if phase_lock:
            powerdown = raw_input("Do you want to power down Synthesizer 2 ? (y/n): ")
            if powerdown.lower()=='y':
               VCOPowerDown(0,switch=1)
            else:
               conf_settings(synth,2)
         else:
            poweron= raw_input('Do you want to power on Synthesizer 2? (y/n):')
            if poweron.lower=='y':
               chg_syn1 = raw_input("Do you want to change the settings of Synthesizer 2? (y/n): ") 
            if chg_syn1.lower() == 'y':
               conf_settings(synth,2)
       
      # saving the current settings
      synth.flash()  
   
      # display current v5007 settings
      display_settings(synth)
  
   else:
      sys.exit()  
        
