"""
Simple gui to talk to Valon 5007
Author: Ridhima Nunhokee 
"""
import Tkinter
from functools import partial
import struct
import serial
import serial.tools.list_ports
import valon_synth as v
import os,sys
import time

class v5007(Tkinter.Tk):
   def __init__(self,parent):
      Tkinter.Tk.__init__(self,parent)
      self.parent = parent

      self[ "bg" ] = 'ivory'

      self.initialize()

   def VSerialPort(self):
      """
      Returns the serial port connected to the valon
 
      """
      portList = []
      for port, desc, hwid in serial.tools.list_ports.comports():
         'Port: ', port, ' Desc: ', desc, ' HwId: ', hwid

      if ( desc.find( "Valon" ) ==0 ):   # on Raspberry Pi
         portList.append( port )
      return portList[0]


   def update_synth(self,*args):
      starttime = time.time()
      self.synth_val = self.option.get()
      if self.synth_val==0:
         pst=8
      else:
         pst=0
      phase_lock = self.synth.get_phase_lock(pst)
      if phase_lock:
          freq = self.synth.get_frequency(self.synth_val)
          ref_freq = float(self.synth.get_reference()) * 1e-6
          min_freq,max_freq = self.synth.get_vco_range(self.synth_val)
          rf = self.synth.get_rf_level(self.synth_val)
          clock = self.synth.get_ref_select()
          vco_opts = self.synth.get_options(self.synth_val)
          self.freqvalue1.set(freq)
          self.freqvalue2.set(ref_freq)
          self.freqvalue3.set(min_freq)
          self.freqvalue4.set(max_freq)
          self.selectedRF.set('Level' +  str(rf))
          self.clockOpt.set(clock)
          self.lck_label.config(text='Locked')
          self.lck_label.config(bg='pink')
          self.powerbutton.config(text='VCO Power Down')
      else:
          self.lck_label.config(bg='pink')
          self.lck_label.config(text='Unlocked')
          self.powerbutton.config(text='VCO Power Up')
      time_elapsed = round(time.time()-starttime,2)
      print 'Time_Elapsed: %s seconds'%time_elapsed 

   def conf(self,*args):
      phase_lock = self.synth.get_phase_lock(self.synth_val)
      if phase_lock:
         inpfreq = float(self.freqvalue1.get())
         inpref_freq = float(self.freqvalue2.get())
         inpmin_freq = float(self.freqvalue3.get())
         inpmax_freq = float(self.freqvalue4.get())
         inpclock = int(self.clockOpt.get())
         rf_level = self.selectedRF.get()
         if (137.5 <= inpfreq <= 4400.0):
            self.synth.set_frequency(self.synth_val,inpfreq)
         else:
            print 'The given frequency beyond the range of V5007. Choose a frequency between 137.5 to 4400 MHz.'
         self.synth.set_vco_range(self.synth_val,inpmin_freq,inpmax_freq)
         rf_level = self.selectedRF.get()
         rf_value = int(rf_level.strip('Level'))
         self.synth.set_rf_level(self.synth_val,rf_value)
         self.synth.set_ref_select(inpclock)
    
   def save(self):
         self.conf()
         self.synth.flash()

   def display(self):
      text = self.display_conf()
      newwin = Tkinter.Toplevel(self)
      config = Tkinter.Label(newwin, text=text,font="times 15 bold",bg='ivory',fg='black')
      config.pack()

   def display_conf(self):
      out = ''
      out +='******************************************************** \n'
      phaselock1 = self.synth.get_phase_lock(v.SYNTH_B)
      phaselock2 = self.synth.get_phase_lock(v.SYNTH_A)
      out += '      SYNTHESIZER 1 \n'
      if phaselock1:
         freq1 = self.synth.get_frequency(v.SYNTH_A)
         rf1 = self.synth.get_rf_level(v.SYNTH_A)
         out += '     Frequency (MHz)        RF Level (dBm) \n'
         out += '%.1f             %s \n'%(freq1,rf1)
      else:
         out += '     Powered Down!  \n'

      out +='\n'
      out += '     SYNTHESIZER 2 \n'
      if phaselock2:
         freq2 = self.synth.get_frequency(v.SYNTH_B)
         rf2 = self.synth.get_rf_level(v.SYNTH_B)
         out += '     Frequency (MHz)        RF Level (dBm) \n'
         out += '%.1f              %s \n'%(freq2,rf2)
      else:
         out += '     Powered Down!  \n'

      out += '********************************************************'
      return out

   def powerDown(self,switch):
      """
      Powering down the synthesizer

      - switch : Switch to power on/off the synthesizer (on/off)
      """
      hexon = 0xBA003C
      hexoff = 0xBA083C
      ACK = 0x06
      port=self.VSerialPort()
      conn = serial.Serial(None, 9600, serial.EIGHTBITS,serial.PARITY_NONE, serial.STOPBITS_ONE)
      conn.setPort(port)
      conn.open()
      def synth_label():
         if self.synth_val==0:
            pst = 0
            label = '1'
         else:
            label= '2'
            pst = 8
         return pst,label
      
      pst,label = synth_label()
      data = struct.pack('>B', 0x80 | pst)
      conn.write(data)
      data=conn.read(24)
      reg0, reg1, reg2, reg3, reg4, reg5 = struct.unpack('>IIIIII', data)

      if switch=='on':
         print 'Powering On Synthesizer %s'%label
         endtxt = 'Synthesizer %s is powered On!'%label
         reg4=hexon
      if switch=='off':
         print 'Powering Off Synthesizer %s'%label
         endtxt = 'Synthesizer %s is powered Down!'%label
         reg4=hexoff

      def _generate_checksum(data):
         "Generate a checksum for the data provided."
         return chr(sum([ord(b) for b in data]) % 256)
      data = struct.pack('>BIIIIII', 0x00 | pst,reg0, reg1, reg2, reg3, reg4, reg5)
      checksum = _generate_checksum(data)
      conn.write(data + checksum)
      data = conn.read(1)
      conn.close()
      ack = struct.unpack('>B', data)[0]
      print endtxt 
      return ack == ACK

   def initialize(self):
      #---Connection Status---
      try:
         # opening the serial port
         port = self.VSerialPort()
         # connecting the synthesizer to serial port
         self.synth = v.Synthesizer(port)
         connection = 'Connected'
         connect = True
      except:
         connection = 'Not Connected'
         connect = False
         print 'Unable to establish connection with the serial port' 
         
      label = Tkinter.Label(self,text='Connection Status',font="times 15 bold",bg='ivory').place(x=360,y=210)
      label = Tkinter.Label(self,text=connection,font="times 15 bold",bg='deeppink',borderwidth=3,relief="raised",width=15).place(x=380,y=240)
         
      #---Header Labels---
      label = Tkinter.Label(self,text='5007 Dual Synthesizer',font=('Comic Sans MS',22,'bold'),borderwidth=4,bg='ivory',fg='red').place(x=8,y=5)

      self.lck_label = Tkinter.Label(self,text='Unknown',font="times 15 bold",bg='gray',borderwidth=3,relief='sunken')
      self.lck_label.place(x=405,y=180)

      self.option = Tkinter.IntVar()
      self.option.trace("w", self.update_synth)
      self.freqvalue1 = Tkinter.DoubleVar()
      self.freqvalue2 = Tkinter.DoubleVar()
      self.freqvalue3 = Tkinter.DoubleVar()
      self.freqvalue4 = Tkinter.DoubleVar()
      self.clockOpt = Tkinter.IntVar()
      self.selectedRF = Tkinter.StringVar()

      #---VCO Settings---
      def noise_enabled():
         if self.noisebutton.config('text')[-1]=='Low Noise Enabled':
            self.synth.set_options(self.synth_val, double = 0, half = 0, divider = 1,low_spur = 0)
            self.noisebutton.config(text='Low PLL Spurs')
         else:
            self.synth.set_options(self.synth_val, double = 0, half = 0, divider = 1,low_spur = 1)
            self.noisebutton.config(text='Low Noise Enabled')

      def buffer_enabled():
         if self.powerbutton.config('text')[-1]=='Double Buffer Enabled':
            self.synth.set_options(self.synth_val, double = 1, half = 0, divider = 1,low_spur = 0)
            self.bufferbutton.config(text='Half Buffer Enabled')
         else:
            self.synth.set_options(self.synth_val, double = 0, half = 0, divider = 1,low_spur = 0)
            self.bufferbutton.config(text='Double Buffer Enabled')

      def power_enabled():
         if self.powerbutton.config('text')[-1]=='VCO Power Down':
            self.powerDown(switch='off')
            self.powerbutton.config(text='VCO Power Up')
            self.lck_label.config(text='Unlocked')
            self.lck_label.config(bg='pink')
         else:
            self.powerbutton.config(text='VCO Power Down')
            self.powerDown(switch='on')
            self.lck_label.config(text='Locked')
            self.lck_label.config(bg='pink')

      label = Tkinter.Label(self,text='VCO Settings',font="times 15 bold",bg='ivory').place(x=360,y=50)
      self.powerbutton = Tkinter.Button(self,text='VCO Power Down',highlightcolor='cyan',width=15,borderwidth=3,relief='raised',command=power_enabled)
      self.powerbutton.place(x=360,y=80)
      label = Tkinter.Label(self,text='VCO Lock Status',font="times 15 bold",bg='ivory',borderwidth=3).place(x=360,y=150)
      

      #---Synthesizers---
      radiobutton1 = Tkinter.Radiobutton(self,text='Synthesizer 1', bg='ivory',value=0,variable=self.option).place(x=300,y=15)
      radiobutton2 = Tkinter.Radiobutton(self,text='Synthesizer 2', bg='ivory',value=8,variable=self.option).place(x=420,y=15)
      self.option.set(8)

      #---Frequency Settings---
      label = Tkinter.Label(self,text='Frequency Settings',font="times 15 bold",bg='ivory').place(x=10,y=50)
      label = Tkinter.Label(self,text='Desired Frequency',bg='ivory').place(x=10,y=80)
      label = Tkinter.Label(self,text='Reference Frequency',bg='ivory').place(x=10,y=110)
      label = Tkinter.Label(self,text='Minimum Frequency',bg='ivory').place(x=10,y=140)
      label = Tkinter.Label(self,text='Maximum Frequency',bg='ivory').place(x=10,y=170)

      label = Tkinter.Label(self,text='MHz',bg='ivory').place(x=280,y=80)
      label = Tkinter.Label(self,text='MHz',bg='ivory').place(x=280,y=110)
      label = Tkinter.Label(self,text='MHz',bg='ivory').place(x=280,y=140)
      label = Tkinter.Label(self,text='MHz',bg='ivory').place(x=280,y=170)
       
      entry1 = Tkinter.Spinbox(width=10,to=4400,from_=137.5,bg='lightgreen',borderwidth=3,textvariable=self.freqvalue1).place(x=160,y=80)
      entry2 = Tkinter.Spinbox(width=10,to=4400,from_=0,bg='lightgreen',borderwidth=3,textvariable=self.freqvalue2).place(x=160,y=110)
      entry3 = Tkinter.Spinbox(width=10,to=4400,from_=137.5,bg='lightgreen',borderwidth=3,textvariable=self.freqvalue3).place(x=160,y=140)
      entry4 = Tkinter.Spinbox(width=10,to=4400,from_=137.5,bg='lightgreen',borderwidth=3,textvariable=self.freqvalue4).place(x=160,y=170)     

      #---Clock Settings---
      self.clockOpt.trace("w", self.conf)
      label = Tkinter.Label(self,text='Clock Settings',font="times 15 bold",bg='ivory').place(x=10,y=220)
      
      radiobutton1 = Tkinter.Radiobutton(self,text='Internal', height=1,bg='ivory',value=0,variable=self.clockOpt).place(x=14,y=250)
      radiobutton2 = Tkinter.Radiobutton(self,text='External', height=1,bg='ivory',value=1,variable=self.clockOpt).place(x=14,y=280)

      #---Power Level---
      label = Tkinter.Label( self, text="Output Power",font="times 15 bold",bg='ivory').place(x=150,y=220)
      
      values = ['Level -4','Level -1','Level 2','Level 5']
      entry = Tkinter.OptionMenu( self,self.selectedRF, *values)
      entry.place(x=170,y=250)
      entry['width']=15
      entry['bg']='ivory'

      #---Display/Save/Quit Button--- 
      button=Tkinter.Button(self,text='Display',bg='gray',command=self.display).place(x=160,y=310)
      button=Tkinter.Button(self,text='Save',bg='gray',command=self.save).place(x=250,y=310)
      button=Tkinter.Button(self,text='Quit',bg='gray',command=self.quit).place(x=330,y=310)


      #---Firmware Verson---
      #label = Tkinter.Label(self,text='Firmware version',font="times 15 bold",bg='ivory').place(x=360,y=240)     
      #label = Tkinter.Label(self,text='1.0.0',font="times 15 bold",bg='gray',width=7,relief='solid').place(x=415,y=270)

      #---Reset Button---
      def reset():
         import os,sys
         os.system('python reset.py')

      button=Tkinter.Button(self,text='Reset',bg='gray',width=15,command=reset).place(x=360,y=110)
      
