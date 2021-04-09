import logging
import time
from AbstractMotor import AbstractMotor, MotorStates
from gevent import Timeout

"""
Interfaces Sardana Motor objects.
taurusname is the only obligatory property.
<device class="SardanaMotor">
    <username>Dummy</username>
    <motor_name>Dummy</motor_name>
    <taurusname>exp_dmy01</taurusname>
    <threshold>0.005</threshold>
    <move_threshold>0.005</move_threshold>
    <interval>2000</interval>
</device>
"""

# TODO: implement nominal velocity concept, missing in Sardana.


class SardanaMotor(AbstractMotor):

    suffix_position = "Position"
    suffix_state = "State"
    suffix_stop = "Stop"
    suffix_velocity = "Velocity"
    suffix_acceleration = "Acceleration"

#    state_map = {
#        "DevState.ON": MotorStates.READY,
#        "DevState.OFF": MotorStates.OFF,
#        "DevState.CLOSE": MotorStates.DISABLED,
#        "DevState.OPEN": MotorStates.DISABLED,
#        "DevState.INSERT": MotorStates.DISABLED,
#        "DevState.EXTRACT": MotorStates.DISABLED,
#        "DevState.MOVING": MotorStates.MOVING,
#        "DevState.STANDBY": MotorStates.READY,
#        "DevState.FAULT": MotorStates.FAULT,
#        "DevState.INIT": MotorStates.INITIALIZING,
#        "DevState.RUNNING": MotorStates.MOVING,
#        "DevState.ALARM": MotorStates.ALARM,
#        "DevState.DISABLE": MotorStates.DISABLED,
#        "DevState.UNKNOWN": MotorStates.UNKNOWN,
#    }

    state_map = {
        "ON": MotorStates.READY,
        "OFF": MotorStates.OFF,
        "CLOSE": MotorStates.DISABLED,
        "OPEN": MotorStates.DISABLED,
        "INSERT": MotorStates.DISABLED,
        "EXTRACT": MotorStates.DISABLED,
        "MOVING": MotorStates.MOVING,
        "STANDBY": MotorStates.READY,
        "FAULT": MotorStates.FAULT,
        "INIT": MotorStates.INITIALIZING,
        "RUNNING": MotorStates.MOVING,
        "ALARM": MotorStates.ALARM,
        "DISABLE": MotorStates.DISABLED,
        "UNKNOWN": MotorStates.UNKNOWN,
    }
    def __init__(self, name):
        AbstractMotor.__init__(self, name)
        self.stop_command = None
        self.position_channel = None
        self.state_channel = None
        self.taurusname = ""
        self.motor_position = 0.0
        self.threshold_default = 0.0018
        self.move_threshold_default = 0.0
        self.polling_default = "events"
        self.limit_upper = None
        self.limit_lower = None
        self.static_limits = (-1E4, 1E4)
        self.limits = (None, None)
        self.motor_state = MotorStates.NOTINITIALIZED

    def init(self):

        try:
            self.taurusname = self.getProperty("taurusname")
        except KeyError:
            logging.getLogger("HWR").warning(
                    "SardanaMotor: taurusname not defined")
            return

        try:
            self.motor_name = self.getProperty("motor_name")
        except KeyError:
            logging.getLogger("HWR").info(
                    "SardanaMotor: motor_name not defined")
            self.motor_name = self.name()

        self.threshold = self.getProperty("threshold", self.threshold_default)
        self.move_threshold = self.getProperty("move_threshold", self.move_threshold_default)

        try:
            self.polling = self.getProperty("interval")
        except KeyError:
            self.polling = None

        if self.polling is None:
            self.polling = self.polling_default

        self.stop_command = self.addCommand({
                    "type": "sardana",
                    "name": self.motor_name + SardanaMotor.suffix_stop,
                    "taurusname": self.taurusname
                }, "Stop")
        self.position_channel = self.addChannel({
                    "type": "sardana",
                    "name": self.motor_name + SardanaMotor.suffix_position,
                    "taurusname": self.taurusname, "polling": self.polling,
                }, "Position")
        self.state_channel = self.addChannel({
                    "type": "sardana",
                    "name": self.motor_name + SardanaMotor.suffix_state,
                    "taurusname": self.taurusname, "polling": self.polling,
                }, "State")

        self.velocity_channel = self.addChannel({
                    "type": "sardana",
                    "name": self.motor_name + SardanaMotor.suffix_velocity,
                    "taurusname": self.taurusname, 
                }, "Velocity")

        self.acceleration_channel = self.addChannel({
                    "type": "sardana",
                    "name": self.motor_name + SardanaMotor.suffix_acceleration,
                    "taurusname": self.taurusname, 
                }, "Acceleration")


        self.position_channel.connectSignal("update", self.motor_position_changed)
        self.state_channel.connectSignal("update", self.motor_state_changed)

        self.limits = self.getLimits()

        (self.limit_lower, self.limit_upper) = self.limits

        if self.limit_lower is None:
            self.limit_lower = self.static_limits[0]

        if self.limit_upper is None:
            self.limit_upper = self.static_limits[1]

    def connectNotify(self, signal):
        if signal == "positionChanged":
            self.motor_position_changed()
        elif signal == "stateChanged":
            self.motor_state_changed()

    def updateState(self):
        """
        Descript. : forces position and state update
        """
        self.motor_position_changed()
        self.motor_state_changed()

    def motor_state_changed(self, state=None):
        """
        Descript. : called by the state channels update event
                    checks if the motor is at it's limit,
                    and sets the new device state
        """
        # This line does what?
        motor_state = self.motor_state
        print('state is %s (type = %s)' % (state, type(state)))
        if state is None:
            state = self.state_channel.getValue()
            print('now state is %s (type = %s)' % (state, type(state)))
            if not state:
                return

        state = state.name
        motor_state = SardanaMotor.state_map[state]

        if motor_state != MotorStates.DISABLED:
            if self.motor_position >= self.limit_upper:
	        motor_state = MotorStates.HIGHLIMIT
            elif self.motor_position <= self.limit_lower:
                motor_state = MotorStates.LOWLIMIT

        self.set_ready(motor_state > MotorStates.DISABLED)

        if motor_state != self.motor_state:
            self.motor_state = motor_state
            self.emit('stateChanged', (motor_state, ))

    def motor_position_changed(self, position=None):
        """
        Descript. : called by the position channels update event
                    if the position change exceeds threshold,
                    positionChanged is fired
        """
        if position is None:
            position = self.position_channel.getValue()

        # logging.getLogger("HWR").debug("SardanaMotor.py position changed. Now is %s" % position)

        if abs(self.motor_position - position) > self.threshold:
            self.motor_position = position
            self.emit('positionChanged', (position, ))
            self.motor_state_changed()

    def getState(self):
        """
        Descript. : returns the current motor state
        """
        self.motor_state_changed()
        return self.motor_state

    def getLimits(self):
        """
        Descript. : returns motor limits. If no limits channel defined then
                    static_limits is returned
        """
        info = self.position_channel.getInfo()

        return (self.limit_lower, self.limit_upper)

    def get_limits(self):
        return self.getLimits()

    def getPosition(self):
        """
        Descript. : returns the current position
        """
        self.motor_position = self.position_channel.getValue()
        return self.motor_position

    def get_position(self):
        return self.getPosition()

    def update_values(self):
        self.emit('limitsChanged', (self.getLimits(), ))
        self.emit('positionChanged', (self.getPosition(), ))

    def getDialPosition(self):
        """
        Descript. :
        """
        return self.getPosition()

    def move(self, absolute_position, wait=False, timeout=None):
        """
        Descript. : move to the given position
        """
        current_pos = self.position_channel.getValue()
        #logging.getLogger("HWR").debug("On move, cached motor_position = %s" % self.motor_position)
        #current_pos = self.getPosition()
        #logging.getLogger("HWR").debug("On move, updated motor position = %s" % current_pos)

        if not current_pos:
            #logging.getLogger("HWR").debug("current position was None")
            current_pos = self.motor_position

        if abs(absolute_position-current_pos) > self.move_threshold_default:
            self.position_channel.setValue(absolute_position)

    def moveRelative(self, relative_position):
        """
        Descript. : move for the given distance
        """
        self.move(self.getPosition() + relative_position)

    def syncMove(self, position, timeout=None):
        """
        Descript. : move to the given position and wait till it's reached
        """
        self.move(position)
        try:
            self.wait_end_of_move(timeout)
        except:
            raise Timeout

    def syncMoveRelative(self, relative_position, timeout=None):
        """
        Descript. : move for the given distance and wait till it's reached
        """
        self.syncMove(self.getPosition() + relative_position, timeout)

    def stop(self):
        """
        Descript. : stops the motor immediately
        """
        self.stop_command()

    def is_moving(self):
        """
        Descript. : True if the motor is currently moving
        """
        return self.isReady() and self.getState() == MotorStates.MOVING

    motorIsMoving = is_moving

    def wait_end_of_move(self, timeout=None):
        """
        Descript. : waits till the motor stops
        """
        with Timeout(timeout):
            time.sleep(0.1)
            while self.is_moving():
                time.sleep(0.1)

    def get_velocity(self):
        try:
            return self.velocity_channel.getValue()            
        except:
            return None

    def set_velocity(self, value):
        self.velocity_channel.setValue(value)            

    def get_acceleration(self):
        try:
            return self.acceleration_channel.getValue()            
        except:
            return None


def test_hwo(hwo):
    newpos = 90
    print("Position for %s is: %s" % (hwo.username, hwo.getPosition()))
    print("Velocity for %s is: %s" % (hwo.username, hwo.get_velocity()))
    print("Acceleration for %s is: %s" % (hwo.username, hwo.get_acceleration()))
    print("Moving motor to %s" % newpos)
    hwo.syncMove(newpos)
    while hwo.is_moving():
        print "Moving"
        time.sleep(0.3)
    print("Movement done. Position is now: %s" % hwo.getPosition())

