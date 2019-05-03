#!/usr/bin/env python

"""
  HardwareObject to collect metadata for MXCuBE experiments
  It should be hooked in data_collection_hook of Collect hardware object
"""
import os
import sys
import logging

from HardwareRepository.BaseHardwareObjects import Device
from HardwareRepository.Command.Tango import DeviceProxy

class MXCuBEMetadataClient(Device):

    def __init__(self, *args):
        Device.__init__(self, *args)

        self.meta_device = None
        self.beamline = None
        self.initialized = False

    def init(self):

        meta_device_name = self.getProperty("tangoname")

        if meta_device_name:
            try:
                self.meta_device = DeviceProxy(meta_device_name)
            except:
                logging.getLogger("HWR").error("Cannot connect to Metadata device servers")
  

        if self.meta_device is None: 
            self.initialized = False
        else:
            self.beamline = self.meta_device.beamline
            self.initialized = True

    def start(self, proposal, dc_pars):
        # Metadata
        if not self.initialized:
            self.init()

        if not self.initialized:
            logging.getLogger("HWR").debug(" - cannot record metadata for experiment")  
            return

        state = self.meta_device.state()

        if state == "RUNNING":
            # Force end of previous scan
            self.meta_device.End()

        fileinfo = dc_pars["fileinfo"]
        directory = fileinfo["directory"]
        prefix = fileinfo["prefix"]
        run_number = int(fileinfo["run_number"])

        sample = prefix
        for type_prefix in ["line-", "mesh-", "ref-", "burn-", "ref-kappa-"]:
            if sample.startswith(type_prefix):
                sample = sample.replace(type_prefix, "")
                break

        collection_id = dc_pars.get('collection_id', '0')
        dataset = "%s_{0}_{1}_{2}".format(self.beamline, prefix, run_number, collection_id)

        self.data_root = directory
        self.sample = sample
        self.dataset = dataset

        try:
            self.meta_device.proposal = proposal
            self.meta_device.dataRoot = directory
            #self.meta_device.datasetName = dataset
            meta_state = str(self.meta_device.state())
            if meta_state == "ON":
                self.meta_device.Start()
        except BaseException:
            logging.getLogger("HWR").debug("Unexpected error:", sys.exc_info()[0])
            raise

        self.print_status()

    def print_status(self):
        print("DataRoot: %s" % self.meta_device.dataRoot)
        print("Proposal: %s" % self.meta_device.proposal)
        print("Dataset:  %s" % self.meta_device.datasetName)
        print(" STATE IS:  %s" % self.meta_device.state())

    def end(self, proposal,  dc_pars, other_pars=None):
        if not self.initialized:
            return

        try:
            # Upload all image files
            fileinfo = dc_pars["fileinfo"]
            collection_id = dc_pars.get('collection_id', '0')
            prefix = fileinfo["prefix"]
            template = fileinfo["template"]
            directory = fileinfo["directory"]
            run_number = int(fileinfo["run_number"])

            for osc_par in dc_pars["oscillation_sequence"]:
                nb_images = osc_par["number_of_images"]
                first_imgno = osc_par["start_image_number"]
                overlap = osc_par["overlap"]
                self.upload_images(dc_pars["fileinfo"], first_imgno, nb_images)

                # Upload the two paths to the meta data HDF5 files
                hdf5_1 = os.path.join(
                    directory,
                    "{proposal}-{beamline}-{prefix}_{run}_{collection_id}.h5".format(
                        beamline=self.beamline,
                        proposal=proposal,
                        prefix=prefix,
                        run=run_number,
                        collection_id=collection_id,
                    ),
                )
                hdf5_2 = os.path.join(
                    directory,
                    "{proposal}-{prefix}-{prefix}_{run}_{collection_id}.h5".format(
                        proposal=proposal,
                        prefix=prefix,
                        run=run_number,
                        collection_id=collection_id,
                    ),
                )

                self.append_file(hdf5_1)
                self.append_file(hdf5_2)

                # Upload meta data as attributes
                # These attributes are common for all ESRF MX beamlines
                metadata = self.get_metadata(dc_pars, other_pars)
                
                for attr_name, value in metadata.iteritems():
                    logging.getLogger("HWR").info(
                        "Setting metadata client attribute '{0}' to '{1}'".format(
                            attr_name, value
                        )
                    )
                    self.meta_device.write_attribute(attr_name, value)

                self.print_status()
                self.meta_device.End()
        except BaseException:
            logging.getLogger("user_level_log").warning("Cannot upload metadata to iCat")
            import traceback
            traceback.print_exc()
            # logging.getLogger("user_level_log").warning(errorMessage)

    def get_metadata(self, dc_pars, other_pars=None):
        """
        Common metadata parameters for ESRF MX beamlines.
          list_attrs must match with Parameters property in MetadataManager DeviceServer
        """
        list_attrs = [
            ["MX_beamShape", "beamShape"],
            ["MX_beamSizeAtSampleX", "beamSizeAtSampleX"],
            ["MX_beamSizeAtSampleY", "beamSizeAtSampleY"],
            ["MX_dataCollectionId", "collection_id"],
            ["MX_directory", "fileinfo.directory"],
            ["MX_exposureTime", "oscillation_sequence.exposure_time"],
            ["MX_flux", "flux"],
            ["MX_fluxEnd", "flux_end"],
            ["MX_numberOfImages", "oscillation_sequence.number_of_images"],
            ["MX_oscillationRange", "oscillation_sequence.range"],
            ["MX_oscillationStart", "oscillation_sequence.start"],
            ["MX_oscillationOverlap", "oscillation_sequence.overlap"],
            ["MX_resolution", "resolution"],
            ["MX_startImageNumber", "oscillation_sequence.start_image_number"],
            ["MX_scanType", "experiment_type"],
            ["MX_template", "fileinfo.template"],
            ["MX_transmission", "transmission"],
            ["MX_xBeam", "xBeam"],
            ["MX_yBeam", "yBeam"],
            ["MX_detectorDistance", "detdistance"],
            ["MX_aperture", "aperture"],
            ["InstrumentMonochromator_wavelength", "wavelength"],
        ]

        metadata = {}
        for attr_name, key_name in list_attrs:
            value = None

            if "." in key_name:
                parent, child = str(key_name).split(".")
                parent_object = dc_pars[parent]
                if isinstance(parent_object, type([])):
                    parent_object = parent_object[0]

                if child in parent_object:
                    value = str(parent_object[child])

            if key_name in dc_pars:
                value = str(dc_pars[key_name])

            if other_pars is not None and key_name in other_pars:
                value = str(other_pars[key_name])

            if value is not None:
                metadata[attr_name] = value

        # Template - replace python formatting with hashes
        metadata["MX_template"] = metadata["MX_template"].replace(
            "%04d", "####"
        )

        # Motor positions
        motor_names = []
        motor_positions = []

        for motor, position in dc_pars["motors"].items():
            if isinstance(motor, str):
                motor_name = motor
            else:
                name_attr = getattr(motor, "name")
                if isinstance(name_attr, str):
                    motor_name = name_attr
                else:
                    motorName = name_attr()

            motor_names.append(motor_name)
            motor_positions.append( str(round(position,3)) )

        metadata["MX_motors_name"] = " ".join(motor_names)
        metadata["MX_motors_value"] = " ".join(motor_positions)

        return metadata

    def append_file(self, file_path):
        try:
            logging.getLogger("HWR").error("  - appending file %s to ICAT" % file_path)
            self.meta_device.lastDataFile = file_path
        except BaseException:
            logging.getLogger("HWR").error("Unexpected error:", sys.exc_info()[0])
            raise

    def upload_images(self, fileinfo, first_imgno, nb_images):

        logging.getLogger("user_level_log").info("Uploading images to ICAT")

        template = fileinfo["template"]
        directory = fileinfo["directory"]

        for index in range(nb_images):
            image_no = index + first_imgno
            image_path = os.path.join(directory, template % image_no)
            self.append_file(image_path)

def test_hwo(hwo):

    proposal = 'u2018002222'

    dc_pars = {
           'collection_id': 23123,
           'fileinfo': {
               'directory': '/beamlines/bl13/projects/cycle2018-II/2018002222-ispybtest/20190409/RAW_DATA',
               'template': 'ref-thau-dummy_name_3_%04d.cbf',
               'prefix': 'ref_thau_dummy_name_',
               'run_number': 3,
           },
           'oscillation_sequence' :
           [{'number_of_images': 10, 'start_image_number':2, 'overlap': 0},],
           'motors' : {'omega': 90, 'phi': 0, 'sampx': 3, 'sampy':0.12},

    }

    hwo.start(proposal, dc_pars)

    other_pars = None
    hwo.print_status()
    # hwo.append_file("/data/visitor/mx415/id30a1/20161014/RAW_DATA/t1/test2.txt")
    hwo.end(proposal, dc_pars, other_pars)
        

