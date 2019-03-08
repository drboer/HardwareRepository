#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
[Name]
ALBAMiniDiff

[Description]
Specific HwObj for M2D2 diffractometer @ ALBA

[Emitted signals]
- pixelsPerMmChanged
- kappaMotorMoved
- phiMotorMoved
- stateChanged
- zoomMotorPredefinedPositionChanged
- minidiffStateChanged
- minidiffPhaseChanged
"""

from __future__ import print_function

import logging
import time
import gevent

import queue_model_objects_v1 as queue_model_objects

from GenericDiffractometer import GenericDiffractometer, DiffractometerState
from taurus.core.tango.enums import DevState

__credits__ = ["ALBA Synchrotron"]
__version__ = "2.3"
__category__ = "General"


class ALBAMiniDiff(GenericDiffractometer):
    """
    Specific diffractometer HwObj for XALOC beamline.
    """

    def __init__(self, *args):
        GenericDiffractometer.__init__(self, *args)
        self.calibration_hwobj = None
        self.centring_hwobj = None
        self.super_hwobj = None
        self.chan_state = None
        self.phi_motor_hwobj = None
        self.phiz_motor_hwobj = None
        self.phiy_motor_hwobj = None
        self.zoom_motor_hwobj = None
        self.focus_motor_hwobj = None
        self.sample_x_motor_hwobj = None
        self.sample_y_motor_hwobj = None
        self.kappa_motor_hwobj = None
        self.kappa_phi_motor_hwobj = None

        self.omegaz_reference = None

    def init(self):

        self.calibration_hwobj = self.getObjectByRole("calibration")

        self.centring_hwobj = self.getObjectByRole('centring')
        self.super_hwobj = self.getObjectByRole('beamline-supervisor')

        if self.centring_hwobj is None:
            logging.getLogger("HWR").debug('ALBAMinidiff: Centring math is not defined')

        if self.super_hwobj is not None:
            self.connect(
                self.super_hwobj,
                'stateChanged',
                self.supervisor_state_changed)
            self.connect(
                self.super_hwobj,
                'phaseChanged',
                self.supervisor_phase_changed)

        self.chan_state = self.getChannelObject("State")
        self.connect(self.chan_state, "update", self.state_changed)

        self.phi_motor_hwobj = self.getObjectByRole('phi')
        self.phiz_motor_hwobj = self.getObjectByRole('phiz')
        self.phiy_motor_hwobj = self.getObjectByRole('phiy')
        self.zoom_motor_hwobj = self.getObjectByRole('zoom')
        self.focus_motor_hwobj = self.getObjectByRole('focus')
        self.sample_x_motor_hwobj = self.getObjectByRole('sampx')
        self.sample_y_motor_hwobj = self.getObjectByRole('sampy')
        self.kappa_motor_hwobj = self.getObjectByRole('kappa')
        self.kappa_phi_motor_hwobj = self.getObjectByRole('kappa_phi')

        if self.phi_motor_hwobj is not None:
            self.connect(
                self.phi_motor_hwobj,
                'stateChanged',
                self.phi_motor_state_changed)
            self.connect(self.phi_motor_hwobj, "positionChanged", self.phi_motor_moved)
        else:
            logging.getLogger("HWR").error('ALBAMiniDiff: Phi motor is not defined')

        if self.phiz_motor_hwobj is not None:
            self.connect(
                self.phiz_motor_hwobj,
                'stateChanged',
                self.phiz_motor_state_changed)
            self.connect(
                self.phiz_motor_hwobj,
                'positionChanged',
                self.phiz_motor_moved)
        else:
            logging.getLogger("HWR").error('ALBAMiniDiff: Phiz motor is not defined')

        if self.phiy_motor_hwobj is not None:
            self.connect(
                self.phiy_motor_hwobj,
                'stateChanged',
                self.phiy_motor_state_changed)
            self.connect(
                self.phiy_motor_hwobj,
                'positionChanged',
                self.phiy_motor_moved)
        else:
            logging.getLogger("HWR").error('ALBAMiniDiff: Phiy motor is not defined')

        if self.zoom_motor_hwobj is not None:
            self.connect(
                self.zoom_motor_hwobj,
                'positionChanged',
                self.zoom_position_changed)
            self.connect(
                self.zoom_motor_hwobj,
                'predefinedPositionChanged',
                self.zoom_motor_predefined_position_changed)
            self.connect(
                self.zoom_motor_hwobj,
                'stateChanged',
                self.zoom_motor_state_changed)
        else:
            logging.getLogger("HWR").error('ALBAMiniDiff: Zoom motor is not defined')

        if self.sample_x_motor_hwobj is not None:
            self.connect(
                self.sample_x_motor_hwobj,
                'stateChanged',
                self.sampleX_motor_state_changed)
            self.connect(
                self.sample_x_motor_hwobj,
                'positionChanged',
                self.sampleX_motor_moved)
        else:
            logging.getLogger("HWR").error('ALBAMiniDiff: Sampx motor is not defined')

        if self.sample_y_motor_hwobj is not None:
            self.connect(
                self.sample_y_motor_hwobj,
                'stateChanged',
                self.sampleY_motor_state_changed)
            self.connect(
                self.sample_y_motor_hwobj,
                'positionChanged',
                self.sampleY_motor_moved)
        else:
            logging.getLogger("HWR").error('ALBAMiniDiff: Sampx motor is not defined')

        if self.focus_motor_hwobj is not None:
            self.connect(
                self.focus_motor_hwobj,
                'positionChanged',
                self.focus_motor_moved)

        if self.kappa_motor_hwobj is not None:
            self.connect(
                self.kappa_motor_hwobj,
                'stateChanged',
                self.kappa_motor_state_changed)
            self.connect(
                self.kappa_motor_hwobj,
                "positionChanged",
                self.kappa_motor_moved)
        else:
            logging.getLogger("HWR").error('ALBAMiniDiff: Kappa motor is not defined')

        if self.kappa_phi_motor_hwobj is not None:
            self.connect(
                self.kappa_phi_motor_hwobj,
                'stateChanged',
                self.kappa_phi_motor_state_changed)
            self.connect(
                self.kappa_phi_motor_hwobj,
                "positionChanged",
                self.kappa_phi_motor_moved)
        else:
            logging.getLogger("HWR").error(
                'ALBAMiniDiff: Kappa-Phi motor is not defined')

        GenericDiffractometer.init(self)

        # overwrite default centring motors configuration from GenericDiffractometer
        # when using sample_centrinig. Fix phiz position to a reference value.
        if self.use_sample_centring:

            if self.getProperty("omegaReference"):
                self.omegaz_reference = eval(self.getProperty("omegaReference"))

                try:
                    logging.getLogger("HWR").debug(
                        "Setting omegaz reference position to {0}".format(
                            self.omegaz_reference['position']))
                    self.centring_phiz.reference_position = \
                        self.omegaz_reference['position']
                except BaseException:
                    logging.getLogger("HWR").warning(
                        "Invalid value for omegaz reference!")
                    raise

        queue_model_objects.CentredPosition.\
            set_diffractometer_motor_names(
                "phi", "phiy", "phiz", "sampx", "sampy", "kappa", "kappa_phi")

        # TODO: Explicit update would not be necessary, but it is.
        # Added to make sure pixels_per_mm is initialised
        self.update_pixels_per_mm()

    def state_changed(self, state):
        """
        Overwrites method to map Tango ON state to Diffractometer State Ready.

        @state: Taurus state but string for Ready state
        """
        if state == DevState.ON:
            state = DiffractometerState.tostring(DiffractometerState.Ready)

        if state != self.current_state:
            logging.getLogger("HWR").debug(
                "ALBAMinidiff: State changed %s (was: %s)" %
                (str(state), self.current_state))
            self.current_state = state
            self.emit("minidiffStateChanged", (self.current_state))

    def getCalibrationData(self, offset=None):
        """
        Get pixel size for OAV system

        @offset: Unused
        @return: 2-tuple float
        """
        calibx, caliby = self.calibration_hwobj.get_calibration()
        return 1000.0 / caliby, 1000.0 / caliby
        # return 1000./self.md2.CoaxCamScaleX, 1000./self.md2.CoaxCamScaleY

    def get_pixels_per_mm(self):
        """
        Returns the pixel/mm for x and y. Overrides GenericDiffractometer method.
        """
        px_x, px_y = self.getCalibrationData()
        return px_x, px_y

    def update_pixels_per_mm(self, *args):
        """
        Emit signal with current pixel/mm values.
        """
        self.pixels_per_mm_x, self.pixels_per_mm_y = self.getCalibrationData()
        self.emit('pixelsPerMmChanged', ((self.pixels_per_mm_x, self.pixels_per_mm_y), ))

    # Overwrite from generic diffractometer
    def update_zoom_calibration(self):
        """
        """
        self.update_pixels_per_mm()

    # TODO: Must be implemented.
    def get_centred_point_from_coord(self, x, y, return_by_names=None):
        """
        Returns a dictionary with motors name and positions centred.
        It is expected in start_move_to_beam and move_to_beam methods in
        GenericDiffractometer HwObj.

        @return: dict
        """
        return {'omega': [200, 200]}

    def getBeamInfo(self, update_beam_callback):
        """
        Update beam info (position and shape) ans execute callback.

        @update_beam_callback: callback method passed as argument.
        """
        size_x = self.getChannelObject("beamInfoX").getValue() / 1000.0
        size_y = self.getChannelObject("beamInfoY").getValue() / 1000.0

        data = {
            "size_x": size_x,
            "size_y": size_y,
            "shape": "ellipse",
        }

        update_beam_callback(data)

    # TODO:Implement dynamically
    def use_sample_changer(self):
        """
        Overrides GenericDiffracometer method.
        """
        return True

    # TODO:Implement dynamically
    def in_plate_mode(self):
        """
        Overrides GenericDiffracometer method.
        """
        return False

    # We are using the sample_centring module. this is not used anymore
    # Not true, we use it!
    def start_manual_centring(self, *args, **kwargs):
        """
        Start manual centring. Overrides GenericDiffracometer method.
        Prepares diffractometer for manual centring.
        """
        if self.prepare_centring():
            GenericDiffractometer.start_manual_centring(self, *args, **kwargs)
        else:
            logging.getLogger("HWR").info(
                " Failed to prepare diffractometer for centring")
            self.invalidate_centring()

    def start_auto_centring(self, *args, **kwargs):
        """
        Start manual centring. Overrides GenericDiffracometer method.
        Prepares diffractometer for manual centring.
        """
        if self.prepare_centring():
            GenericDiffractometer.start_auto_centring(self, *args, **kwargs)
        else:
            logging.getLogger("HWR").info(
                " Failed to prepare diffractometer for centring")
            self.invalidate_centring()

    def prepare_centring(self):
        """
        Prepare beamline for to sample_view phase.
        """
        if not self.is_sample_view_phase():
            logging.getLogger("HWR").info(
                " Not in sample view phase. Asking supervisor to go")
            success = self.go_sample_view()
            if not success:
                logging.getLogger("HWR").info("Cannot set SAMPLE VIEW phase")
                return False

        return True

    def is_sample_view_phase(self):
        """
        Returns boolean by comparing the supervisor current phase and SAMPLE view phase.

        @return: boolean
        """
        return self.super_hwobj.get_current_phase().upper() == "SAMPLE"

    def go_sample_view(self):
        """
        Go to sample view phase.
        """
        self.super_hwobj.go_sample_view()

        while True:
            super_state = self.super_hwobj.get_state()
            logging.getLogger("HWR").debug(
                'ALBAMinidiff: waiting for go_sample_view done (supervisor state is %s)'
                % super_state)
            if super_state != DevState.MOVING:
                logging.getLogger("HWR").debug(
                    'ALBAMinidiff: go_sample_view done (%s)' %
                    super_state)
                return True
            gevent.sleep(0.2)

    def supervisor_state_changed(self, state):
        """
        Emit stateChanged signal according to supervisor current state.
        """
        return
        self.current_state = state
        self.emit('stateChanged', (self.current_state, ))

    # TODO: Review override current_state by current_phase
    def supervisor_phase_changed(self, phase):
        """
        Emit stateChanged signal according to supervisor current phase.
        """
        #self.current_state = phase
        self.emit('minidiffPhaseChanged', (phase, ))

    def phi_motor_moved(self, pos):
        """
        Emit phiMotorMoved signal with position value.
        """
        self.current_motor_positions["phi"] = pos
        self.emit("phiMotorMoved", pos)

    def phi_motor_state_changed(self, state):
        """
        Emit stateChanged signal with state value.
        """
        self.current_motor_states["phi"] = state
        self.emit('stateChanged', (state, ))

    def phiz_motor_moved(self, pos):
        """
        """
        self.current_motor_positions["phiz"] = pos

    def phiz_motor_state_changed(self, state):
        """
        Emit stateChanged signal with state value.
        """
        self.emit('stateChanged', (state, ))

    def phiy_motor_state_changed(self, state):
        """
        Emit stateChanged signal with state value.
        """
        self.emit('stateChanged', (state, ))

    def phiy_motor_moved(self, pos):
        """
        """
        self.current_motor_positions["phiy"] = pos

    def zoom_position_changed(self, value):
        """
        Update positions after zoom changed.

        @value: zoom position.
        """
        self.update_pixels_per_mm()
        self.current_motor_positions["zoom"] = value
        self.refresh_omega_reference_position()

    def zoom_motor_predefined_position_changed(self, position_name, offset):
        """
        Update pixel size and emit signal.
        """
        self.update_pixels_per_mm()
        self.emit('zoomMotorPredefinedPositionChanged',
                  (position_name, offset, ))

    def zoom_motor_state_changed(self, state):
        """
        Emit signal for motor zoom changed

        @state: new state value to emit.
        """
        self.emit('stateChanged', (state, ))

    def sampleX_motor_moved(self, pos):
        """
        """
        self.current_motor_positions["sampx"] = pos

    def sampleX_motor_state_changed(self, state):
        """
        Emit stateChanged signal with state value.
        """
        self.current_motor_states["sampx"] = state
        self.emit('stateChanged', (state, ))

    def sampleY_motor_moved(self, pos):
        """
        """
        self.current_motor_positions["sampy"] = pos

    def sampleY_motor_state_changed(self, state):
        """
        Emit stateChanged signal with state value.
        """
        self.current_motor_states["sampy"] = state
        self.emit('stateChanged', (state, ))

    def kappa_motor_moved(self, pos):
        """
        Emit kappaMotorMoved signal with position value.
        """
        self.current_motor_positions["kappa"] = pos
        self.emit("kappaMotorMoved", pos)

    def kappa_motor_state_changed(self, state):
        """
        Emit stateChanged signal with state value.
        """
        self.current_motor_states["kappa"] = state
        self.emit('stateChanged', (state, ))

    def kappa_phi_motor_moved(self, pos):
        """
        Emit kappa_phiMotorMoved signal with position value.
        """
        self.current_motor_positions["kappa_phi"] = pos
        self.emit("kappa_phiMotorMoved", pos)

    def kappa_phi_motor_state_changed(self, state):
        """
        Emit stateChanged signal with state value.
        """
        self.current_motor_states["kappa_phi"] = state
        self.emit('stateChanged', (state, ))

    def focus_motor_moved(self, pos):
        """
        """
        self.current_motor_positions["focus"] = pos

    def start_auto_focus(self):
        pass

    def move_omega(self, pos, velocity=None):
        """
        Move omega to absolute position.

        @pos: target position
        """
        # turn it on
        if velocity is not None:
            self.phi_motor_hwobj.set_velocity(velocity)
        self.phi_motor_hwobj.move(pos)
        time.sleep(0.2)
        # it should wait here

    def move_omega_relative(self, relpos):
        """
        Move omega to relative position.

        @relpos: target relative position
        """
        self.wait_device_ready()
        self.phi_motor_hwobj.syncMoveRelative(relpos)
        time.sleep(0.2)
        self.wait_device_ready()

    # TODO: define phases as enum members.
    def set_phase(self, phase):
        """
        General function to set phase by using supervisor commands.
        """
        if phase == "Transfer":
            self.super_hwobj.go_transfer()
        elif phase == "Collect":
            self.super_hwobj.go_collect()
        elif phase == "BeamView":
            self.super_hwobj.go_beam_view()
        elif phase == "Centring":
            self.super_hwobj.go_sample_view()
        else:
            logging.getLogger("HWR").warning(
                "Diffractometer set_phase asked for un-handled phase: %s" %
                phase)


def test_hwo(hwo):
    print(hwo.get_phase_list())
