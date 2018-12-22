import visa
import time
import numpy as np

READ_TERMINATION  = '\r'
WRITE_TERMINATION = '\r'

#READ_TERMINATION  = '\r\n'
#WRITE_TERMINATION = '\r\n'

class SourceMeterServer(object):

    def __init__(self,port):
        self.port = port
        self.isOpen = False
        self.open()

        self.alias_sense = {
            'VOLT':'VOLT', 'CURR':'CURR', 'RES':'RES',
            'volt':'VOLT', 'curr':'CURR', 'res':'RES',
            'V'   :'VOLT', 'C'   :'CURR', 'R'  :'RES',
            'v'   :'VOLT', 'c'   :'CURR', 'r'  :'RES',
            }

        self.alias_source = {
            'VOLT':'VOLT', 'CURR':'CURR',
            'volt':'VOLT', 'curr':'CURR',
            'V'   :'VOLT', 'C'   :'CURR',
            'v'   :'VOLT', 'c'   :'CURR',
            }
           

        ###These are set to true after the mode is changed. They are reset to false if a low level write operation is performed
        self.Vout=False
        self.Iout=False

        self.Vsense=False
        self.Isense=False
        self.Rsense=False
        self.remoteOn=False
        self.outpOn=False

    ##########################################
    #  Opening and closing visa connections  #
    ##########################################
    def close(self):
        """Closes the connection to the COM port"""
        if self.isOpen:
            self._cxn.close()
            self.isOpen = False
        else:
            raise ValueError("Connection already closed")
    def open(self):
        if not(self.isOpen):
            self._rm  = visa.ResourceManager()
            self._cxn = self._rm.open_resource(
                "COM{n}".format(n=self.port),
                read_termination=READ_TERMINATION,
                write_termination=WRITE_TERMINATION,
                )
            self.isOpen = True # wheter or not the connection is open
        else:
            raise ValueError("Connection already open")
       

    def rstFlags(self,default=False):
            self.Vout=False
            self.Iout=False
            
            self.remoteOn=False
            self.outpOn=False
            if default:
                self.Vsense=True
                self.Isense=True
                self.Rsense=True
            else:    
                self.Vsense=False
                self.Isense=False
                self.Rsense=False


    ##########################
    #  LOW-LEVEL READ/WRITE  #
    ##########################
    ###when using public write methods the flags are reset to false 

    def write(self,data):
        if self.isOpen:
            self._cxn.write(data)
            self.rstFlags()
        else:
            raise ValueError("Connection is closed")
        
    
    def write_raw(self,data):
        if self.isOpen:
            self._cxn.write_raw(data)
            self.rstFlags()
        else:
            raise ValueError("Connection is closed")
        
    
    def read(self):
        if self.isOpen:
            return self._cxn.read()
        else:
            raise ValueError("Connection is closed")

    ###the private write method should be used if the flags are taken care of by the method calling it
    def __write(self,data):
        if self.isOpen:
            self._cxn.write(data)
        else:
            raise ValueError("Connection is closed")



    ############################
    #  SYSTEM + MISC COMMANDS  #
    ############################
    def reset(self):
        """Resets the SourceMeter"""
        self.__write("*RST")
        self.rstFlags(default=True) 
    def remote_on(self):
        self.__write(":SYST:RSEN ON")
        self.remoteOn=True
    def remote_off(self):
        self.__write(":SYST:RSEN OFF")
        self.remoteOn=False




    #############################
    #  SOURCE (SOUR) FUNCTIONS  #
    #############################

    def source_mode(self,setto=None):
        if setto == None:
            self.__write(":SOUR:FUNC:MODE?")
            return self.read()
        else:
            if setto in self.alias_source.keys():
                self.__write(":SOUR:FUNC {setto}".format(setto=self.alias_source[setto]))
                #print (":SOUR:FUNC {setto}".format(setto=self.alias_source[setto]))
                if self.alias_source[setto]=='VOLT': 
                    self.Vout=True
                    self.Iout=False
                if self.alias_source[setto]=='CURR': 
                    self.Vout=False
                    self.Iout=True
            else:
                raise ValueError("Invalid source mode")

    def source_voltage_range(self,setto=None):
        if setto == None:
            self.__write(":SOUR:VOLT:RANG?")
            return float(self.read())
        else:
            if self.Vout==True:
                self.__write(":SOUR:VOLT:RANG {setto}".format(setto=setto))
            else:
                raise ValueError("Not in voltage source mode")

    def source_current_range(self,setto=None):
        if setto == None:

            self.__write(":SOUR:CURR:RANG?")
            return float(self.read())
        else:
            if self.Iout==True:
                self.__write(":SOUR:CURR:RANG {setto}".format(setto=setto))
            else:
                raise ValueError("Not in current source mode")

    def source_voltage_level(self,setto=None):
        if setto == None:
            self.__write(":SOUR:VOLT:LEV?")
            return float(self.read())
        else:
            if self.Vout==True:
                self.__write(":SOUR:VOLT:LEV {setto}".format(setto=setto))
            else:
                raise ValueError("Not in voltage source mode")

    def source_current_level(self,setto=None):
        if setto == None:
            self.__write(":SOUR:CURR:LEV?")
            return float(self.read())
        else:
            if self.Iout==True:
                self.__write(":SOUR:CURR:LEV {setto}".format(setto=setto))
            else:
                raise ValueError("Not in current source mode")





    ###########################
    # OUTPUT (OUTP) FUNCTIONS #
    ###########################
    def output_on(self):
        self.__write(":OUTP ON")
        self.outpOn=True
    def output_off(self):
        self.__write(":OUTP OFF")
        self.outpOn=False



    ##########################
    # SENSE (SENS) FUNCTIONS #
    ##########################

    def sense_off_all(self):
        self.__write(":SENS:FUNC:OFF:ALL")
        self.Vsense=False
        self.Isense=False
        self.Rsense=False
    
    def sense_on_all(self):
        self.__write(":SENS:FUNC:ON:ALL")
        self.Vsense=True
        self.Isense=True
        self.Rsense=True

    def sense_on(self,which):
        if not (which in self.alias_sense.keys()):
            raise ValueError("Invalid sense setting")
        self.__write(":SENS:FUNC:ON '{which}'".format(which=self.alias_sense[which]))
        if self.alias_sense[which]=='VOlT':
            self.Vsense=True
        if self.alias_sense[which]=='CURR':
            self.Isense=True
        if self.alias_sense[which]=='RES':
            self.Rsense=True
            
    def sense_off(self,which):
        if not (which in self.alias_sense.keys()):
            raise ValueError("Invalid sense setting")
        self.__write(":SENS:FUNC:OFF '{which}'".format(which=self.alias_sense[which]))
        if self.alias_sense[which]=='VOlT':
            self.Vsense=False
        if self.alias_sense[which]=='CURR':
            self.Isense=False
        if self.alias_sense[which]=='RES':
            self.Rsense=False
         
    def get_active_sense_functions(self):
        self.__write(":SENS:FUNC:ON?")
        ans = self.read()
        if ans == '""': # no active functions
            return []
        active = []
        while ',' in ans:
            channel,_,ans = ans.partition(',')
            active.append(channel)
        active.append(ans)
        return active

    def get_inactive_sense_functions(self):
        self.__write(":SENS:FUNC:OFF?")
        ans=self.read()
        if ans == '""': # no inactive functions
            return []
        inactive = []
        while ',' in ans:
            channel,_,ans = ans.partition(',')
            inactive.append(channel)
        inactive.append(ans)
        return inactive

    def sense_current_range(self,setto=None):
        if setto == None:
            self.__write(":SENS:CURR:RANG?")
            return self.read()
        if setto=='AUTO':
            self.__write(":SENS:CURR:RANG:AUTO ON")
        else:
            print ("setting I range")
            print ("\nrange\n",self.sense_current_range())
            self.__write(":SENS:CURR:RANG {setto}".format(setto=setto))
            print ("\nrange\n",self.sense_current_range())
    def sense_current_prot(self,setto=None):
        if setto == None:
            self.__write(":SENS:CURR:PROT?")
            return self.read()
        else:
            self.__write(":SENS:CURR:PROT {setto}".format(setto=setto))
    
    def sense_voltage_range(self,setto=None):
        if setto == None:
            self.__write(":SENS:VOLT:RANG?")
            return self.read()
        else:
            self.__write(":SENS:VOLT:RANG {setto}".format(setto=setto))
    
    def sense_voltage_prot(self,setto=None):
        if setto == None:
            self.__write(":SENS:VOLT:PROT?")
            return self.read()
        else:
            self.__write(":SENS:VOLT:PROT {setto}".format(setto=setto))

    def format_data(self, setto=None):
        if setto == None:
            self.__write(":FORM:ELEM?")
            return self.read()
        else:
            self.__write(":FORM:ELEM {setto}".format(setto=setto))

    def meas(self):
        return self.__write(":READ?")




    #########################################
    # Routines for IV curves, pedestal, etc #
    #########################################
class MakeIVCurve(object):

    def __init__(self, sourceMeterServer):
        self.s=sourceMeterServer

    

    def advance(self,timeEl):
        pass
        

    def set_V_out_I_sense(self,setto=None, protI=None, rangeI=None):
        self.s.sense_off('VOLT')
        self.s.sense_off('RES')
        if setto==None:
            raise ValueError("No voltage value specified")
        else:

            #if self.remoteOn==False:
            #    self.remote_on()

            if self.s.Vout==False:
               self.s.source_mode('VOLT')

            if protI is not None:
                self.s.sense_current_prot(setto=protI)

                   
            if rangeI is not None:
                self.s.sense_current_range(setto=rangeI)


            self.s.source_voltage_level(setto)

            if self.s.Isense==False:
               self.s.sens_on('CURR')

   
            if self.s.outpOn==False:
                self.s.output_on()    

    def ramp_volt_up(self, startV=0, stopV=50, waitT=30, step=5, maxI=1*10**(-6), rangeI=None ):

        measCurrent=[]

        self.s.format_data("CURR")

        vPoints=np.arange(startV, stopV+step, step)
        measPoints=[]
        for vStep in vPoints:

            if vStep==startV:
                self.set_V_out_I_sense(setto=vStep, protI=maxI, rangeI=rangeI)
                time.sleep(waitT)
                self.s.meas()
                currentReading=self.s.read()
                measCurrent.append(currentReading)
                measPoints.append(vStep)
            else:
                self.set_V_out_I_sense(setto=vStep, protI=maxI, rangeI='AUTO')
                time.sleep(waitT)
                self.s.meas()
                currentReading=self.s.read()
                measCurrent.append(currentReading)
                measPoints.append(vStep)
                
            print (vStep,currentReading)
            
            if float(currentReading)>maxI*0.95:
                print ("Max current reached before reaching the max set voltage")
                measPoints=np.array(measPoints)
                break 
            
        measPoints=np.array(measPoints)
        measCurrent=np.array(measCurrent)
        return np.array([measPoints,measCurrent])
        


    def ramp_volt_down(self, startV=0, stopV=50, waitT=30, step=5, maxI=1*10**(-6), rangeI=None):
        measCurrent=[]

        self.s.format_data("CURR")
        vPoints=np.arange(stopV, startV+step, step)[::-1]

        for vStep in vPoints:

            if vStep==startV:
                self.set_V_out_I_sense(setto=vStep, protI=maxI, rangeI=rangeI)
                time.sleep(waitT)
                self.s.meas()
                currentReading=self.s.read()
                measCurrent.append(currentReading)
            else:
                self.set_V_out_I_sense(setto=vStep, protI=maxI, rangeI='AUTO')
                time.sleep(waitT)
                self.s.meas()
                currentReading=self.s.read()
                measCurrent.append(currentReading)

            print (vStep,currentReading)


        measCurrent=np.array(measCurrent)
        return np.array([vPoints,measCurrent])

    def makeIVCurve(self, startV=0, stopV=50, waitT=30, step=5, maxI=1*10**(-6), rangeI=None):
        self.s.reset()
        rampUp=self.ramp_volt_up(startV=startV, stopV=stopV, waitT=waitT, step=step, maxI=maxI, rangeI=rangeI )
        downStart=float(rampUp[0][-1])
        
        rampDown=self.ramp_volt_down(startV=downStart, stopV=startV, waitT=waitT, step=step, maxI=maxI, rangeI=rangeI)
        self.s.output_off()
        return(rampDown,rampUp)




if __name__ == '__main__':
    pass

if False:
    s = SourceMeterServer(4)
    v='VOLT'
    c='CURR'
    r='RES'
    s.reset()
    #s.sense_on(r)
    #s.format_data(r)
    #s.output_on()
    #s.meas()
    #print('r',s.read())
    #print (s.get_active_sense_functions())
    #s.output_off()
    #s.sense_off(r)
    IVc=MakeIVCurve(s)
    IV=IVc.makeIVCurve(startV=0, stopV=3, waitT=3, step=1, maxI=10*10**(-4), rangeI=None)

    
    print ("IV",IV[0])
    print ('rampup',IV[1])
    quit()
    curr=s.ramp_volt_up(startV=0, stopV=10, waitT=3, step=1, maxI=10**(-3), rangeI=None)
    print (curr)
    curr=s.ramp_volt_down(startV=10, stopV=0, waitT=3, step=1, maxI=10**(-3), rangeI=None)
    print (curr)
    s.write(":OUTP OFF")
    s.remote_off()
    quit()
    s.output_on()
    #s.write(":SOUR:FUNC VOLT")
    #s.write(":SOUR:VOLT 2")
    s.source_mode(v)
    s.source_voltage_level(2)
    quit()
    s.sense_on(c)
    #s.write(":SENS:FUNC 'CURR'")
    s.write(":SENS:CURR:RANG:AUTO ON")
    s.write(":SENS:CURR:PROT:LEV 0.002")
    s.output_on()
    #s.write(":TRIG:COUN 1")
    s.write(":FORM:ELEM CURR,VOLT")
    s.meas()
    print (s.read())

    #s.write(":SOUR:FUNC VOLT")
    s.write(":SOUR:VOLT 1")
    #s.sense_on(c)
    #s.write(":SENS:FUNC 'CURR'")
    #s.write(":SENS:CURR:RANG:AUTO ON")
    #s.write(":SENS:CURR:PROT:LEV 0.002")
    #s.output_on()
    #s.write(":TRIG:COUN 1")
    s.write(":FORM:ELEM CURR,VOLT")
    s.meas()
    print (s.read())
    print ("querying output")
    print ("turning off output")
    s.write(":OUTP OFF")

