# coding=utf-8
"""
Created on 4.5.2018
Updated on 21.8.2018

Potku is a graphical user interface for analyzation and
visualization of measurement data collected from a ToF-ERD
telescope. For physics calculations Potku uses external
analyzation components.
Copyright (C) 2013-2018 Jarkko Aalto, Severi Jääskeläinen, Samuel Kaiponen,
Timo Konu, Samuli Kärkkäinen, Samuli Rahkonen, Miika Raunio, Heta Rekilä and
Sinikka Siironen

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program (file named 'LICENCE').
"""

__author__ = "Severi Jääskeläinen \n Samuel Kaiponen \n Heta Rekilä " \
             "\n Sinikka Siironen"
__version__ = "2.0"

import modules.masses as masses
import os
import shutil
import time

from dialogs.element_selection import ElementSelectionDialog

from modules.detector import Detector
from modules.general_functions import set_input_field_red
from modules.run import Run
from modules.target import Target

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5 import uic

from widgets.detector_settings import DetectorSettingsWidget
from widgets.measurement.settings import MeasurementSettingsWidget
from widgets.profile_settings import ProfileSettingsWidget


class MeasurementSettingsDialog(QtWidgets.QDialog):
    """
    Dialog class for handling the measurement parameter input.
    """

    def __init__(self, measurement, icon_manager):
        """
        Initializes the dialog.

        Args:
            measurement: A Measurement object whose parameters are handled.
            icon_manager: An icon manager.
        """
        super().__init__()
        self.measurement = measurement
        self.icon_manager = icon_manager
        self.ui = uic.loadUi(os.path.join("ui_files",
                                          "ui_specific_settings.ui"), self)
        self.ui.setWindowTitle("Measurement Settings")
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        screen_geometry = QtWidgets.QDesktopWidget.availableGeometry(
            QtWidgets.QApplication.desktop())
        self.resize(self.geometry().width() * 1.1,
                    screen_geometry.size().height()
                    * 0.8)
        self.ui.defaultSettingsCheckBox.stateChanged.connect(
            lambda: self.__change_used_settings())
        self.ui.OKButton.clicked.connect(lambda:
                                         self.__save_settings_and_close())
        self.ui.applyButton.clicked.connect(lambda: self.__update_parameters())
        self.ui.cancelButton.clicked.connect(self.close)

        # Add measurement settings view to the settings view
        self.measurement_settings_widget = MeasurementSettingsWidget(
            self.measurement)
        self.ui.tabs.addTab(self.measurement_settings_widget, "Measurement")

        self.measurement_settings_widget.ui.picture.setScaledContents(True)
        pixmap = QtGui.QPixmap(os.path.join("images",
                                            "measurement_setup_angles.png"))
        self.measurement_settings_widget.ui.picture.setPixmap(pixmap)

        self.measurement_settings_widget.ui.beamIonButton.clicked.connect(
            lambda: self.__change_element(
                self.measurement_settings_widget.ui.beamIonButton,
                self.measurement_settings_widget.ui.isotopeComboBox))

        # Add detector settings view to the settings view
        if self.measurement.detector:
            detector_object = self.measurement.detector
        else:
            detector_object = self.measurement.request.default_detector
        self.detector_settings_widget = DetectorSettingsWidget(
            detector_object, self.measurement.request, self.icon_manager,
            self.measurement_settings_widget.tmp_run)

        self.ui.tabs.addTab(self.detector_settings_widget, "Detector")

        if self.measurement.detector is not None:
            self.ui.defaultSettingsCheckBox.setCheckState(0)
            self.measurement_settings_widget.ui.nameLineEdit.setText(
                self.measurement.measurement_setting_file_name)
            self.measurement_settings_widget.ui.descriptionPlainTextEdit \
                .setPlainText(
                    self.measurement.measurement_setting_file_description)
            self.measurement_settings_widget.ui.dateLabel.setText(time.strftime(
                "%c %z %Z", time.localtime(self.measurement.modification_time)))

        # Add profile settings view to the settings view
        self.profile_settings_widget = ProfileSettingsWidget(
            self.measurement)
        self.ui.tabs.addTab(self.profile_settings_widget, "Profile")

        self.ui.tabs.currentChanged.connect(lambda: self.__check_for_red())

        self.__close = True

        self.exec()

    def __change_element(self, button, combo_box):
        """ Opens element selection dialog and loads selected element's isotopes
        to a combobox.

        Args:
            button: button whose text is changed accordingly to the made
            selection.
        """
        dialog = ElementSelectionDialog()
        if dialog.element:
            button.setText(dialog.element)
            # Enabled settings once element is selected
            self.__enabled_element_information()
            masses.load_isotopes(dialog.element, combo_box)

            # Check if no isotopes
            if combo_box.count() == 0:
                self.measurement_settings_widget.ui.isotopeInfoLabel \
                    .setVisible(True)
                self.measurement_settings_widget.fields_are_valid = False
                set_input_field_red(combo_box)
            else:
                self.measurement_settings_widget.ui.isotopeInfoLabel \
                    .setVisible(False)
                self.measurement_settings_widget.check_text(
                    self.measurement_settings_widget.ui.nameLineEdit,
                    self.measurement_settings_widget)
                combo_box.setStyleSheet("background-color: %s" % "None")

    def __change_used_settings(self):
        check_box = self.sender()
        if check_box.isChecked():
            self.ui.tabs.setEnabled(False)
        else:
            self.ui.tabs.setEnabled(True)

    def __check_for_red(self):
        """
        Check whether there are any invalid field in the tabs.
        """
        for i in range(self.ui.tabs.count()):
            tab_widget = self.ui.tabs.widget(i)
            valid = tab_widget.fields_are_valid
            if not valid:
                self.ui.tabs.blockSignals(True)
                self.tabs.setCurrentWidget(tab_widget)
                self.ui.tabs.blockSignals(False)
                break

    def __enabled_element_information(self):
        """ Change the UI accordingly when an element is selected.
        """
        self.measurement_settings_widget.ui.isotopeComboBox.setEnabled(True)
        self.measurement_settings_widget.ui.isotopeLabel.setEnabled(True)
        self.ui.OKButton.setEnabled(True)

    def __update_parameters(self):
        """ Update Measurement's Run, Detector and Target objects. If measurement
         specific parameters are in use, save them into a file.
        """
        if self.measurement_settings_widget.ui.isotopeComboBox.currentIndex()\
                == -1:
            QtWidgets.QMessageBox.critical(self, "Warning",
                                           "No isotope selected.\n\nPlease "
                                           "select an isotope for the beam "
                                           "element.",
                                           QtWidgets.QMessageBox.Ok,
                                           QtWidgets.QMessageBox.Ok)
            self.__close = False
            return

        if not self.measurement.measurement_setting_file_name:
            self.measurement.measurement_setting_file_name = \
                self.measurement.name
        if not self.measurement.profile_name:
            self.measurement.profile_name = self.measurement.name

        check_box = self.ui.defaultSettingsCheckBox
        if check_box.isChecked():
            # Use request settings
            measurement = self.measurement.request.default_measurement
            self.measurement.run = None
            self.measurement.detector = None
            self.measurement.use_default_profile_settings = True
            self.measurement.measurement_setting_file_description = \
                measurement.measurement_setting_file_description
            self.measurement.target = None

            # Revert all profile parameters to default.
            self.measurement.profile_description = \
                measurement.profile_description
            self.measurement.reference_density = measurement.reference_density
            self.measurement.number_of_depth_steps = \
                measurement.number_of_depth_steps
            self.measurement.depth_step_for_stopping = \
                measurement.depth_step_for_stopping
            self.measurement.depth_step_for_output = \
                measurement.depth_step_for_output
            self.measurement.depth_for_concentration_from = \
                measurement.depth_for_concentration_from
            self.measurement.depth_for_concentration_to = \
                measurement.depth_for_concentration_to
            self.measurement.channel_width = measurement.channel_width
            self.measurement.number_of_splits = measurement.number_of_splits
            self.measurement.normalization = measurement.normalization

            det_folder_path = os.path.join(self.measurement.directory,
                                           "Detector")
            if os.path.exists(det_folder_path):
                # Remove Measurement specific Detector files
                shutil.rmtree(det_folder_path)

            filenames_to_remove = []
            for file in os.listdir(self.measurement.directory):
                if file.endswith(".measurement") or file.endswith(".profile")\
                        or file.endswith(".target"):
                    filenames_to_remove.append(file)
            for file in filenames_to_remove:
                # Remove Measurement specific .measurement and .profile files
                os.remove(os.path.join(self.measurement.directory, file))
            self.__close = True
        else:
            # Check the target and detector angles
            ok_pressed = self.measurement_settings_widget.check_angles()
            if ok_pressed:
                if not self.ui.tabs.currentWidget().fields_are_valid:
                    QtWidgets.QMessageBox.critical(self, "Warning",
                                                   "Some of the setting values "
                                                   "have not been set.\n" +
                                                   "Please input values in "
                                                   "fields indicated in red.",
                                                   QtWidgets.QMessageBox.Ok,
                                                   QtWidgets.QMessageBox.Ok)
                    self.__close = False
                    return
                # Use Measurement specific settings
                try:
                    self.measurement.use_default_profile_settings = False
                    if self.measurement.measurement_setting_file_name is None:
                        file_name = "temp"
                    else:
                        file_name = self.measurement.\
                            measurement_setting_file_name

                    if self.measurement.target is None:
                        # Create default Target object for Measurement
                        self.measurement.target = Target()
                    if self.measurement.run is None:
                        # Create default Run object for Measurement
                        self.measurement.run = Run()

                    det_folder_path = \
                        os.path.join(self.measurement.directory, "Detector")
                    measurement_settings_file_path = \
                        os.path.join(self.measurement.directory,
                                     file_name + ".measurement")

                    if self.measurement.detector is None:
                        # Create default Detector object for Measurement
                        detector_file_path = os.path.join(det_folder_path,
                                                          "Default.detector")
                        if not os.path.exists(det_folder_path):
                            os.makedirs(det_folder_path)
                        self.measurement.detector = Detector(
                            detector_file_path, measurement_settings_file_path)
                        self.measurement.detector.update_directories(
                            det_folder_path)
                        # Transfer the default detector efficiencies to
                        # new Detector
                        self.measurement.detector.efficiencies = list(
                            self.measurement.request.default_detector.
                            efficiencies)
                        self.measurement.request.default_detector.efficiencies \
                            = []

                    # Set Detector object to settings widget
                    self.detector_settings_widget.obj = self.measurement.\
                        detector

                    # Update settings
                    self.measurement_settings_widget.update_settings()
                    self.detector_settings_widget.update_settings()

                    for file in self.measurement.detector.efficiencies:
                        self.measurement.detector.add_efficiency_file(file)

                    for file in \
                            self.measurement.detector.efficiencies_to_remove:
                        self.measurement.detector.remove_efficiency_file(
                            file)

                    self.profile_settings_widget.update_settings()
                    self.measurement.detector.path = \
                        os.path.join(det_folder_path,
                                     self.measurement.detector.name +
                                     ".detector")

                    # Delete possible extra .measurement and .profile files
                    filenames_to_remove = []
                    for file in os.listdir(self.measurement.directory):
                        if file.endswith(".measurement") or file.endswith(
                                ".profile"):
                            filenames_to_remove.append(file)
                    for filename in filenames_to_remove:
                        os.remove(os.path.join(self.measurement.directory,
                                               filename))

                    # Save general measurement settings parameters.
                    new_measurement_settings_file_path = os.path.join(
                        self.measurement.directory,
                        self.measurement.measurement_setting_file_name +
                        ".measurement")
                    self.measurement\
                        .measurement_to_file(new_measurement_settings_file_path)

                    # Save run parameters
                    self.measurement.run.to_file(
                        new_measurement_settings_file_path)
                    # Save detector parameters
                    self.measurement.detector.to_file(
                        self.measurement.detector.path,
                        new_measurement_settings_file_path)

                    # Save profile parameters
                    profile_file_path = \
                        os.path.join(self.measurement.directory,
                                     self.measurement.profile_name + ".profile")
                    self.measurement.profile_to_file(profile_file_path)

                    # Save target parameters
                    target_file_path = \
                        os.path.join(self.measurement.directory,
                                     self.measurement.target.name + ".target")
                    self.measurement.target\
                        .to_file(target_file_path,
                                 new_measurement_settings_file_path)

                    self.__close = True

                except TypeError:
                    QtWidgets.QMessageBox.question(self, "Warning",
                                                   "Some of the setting values "
                                                   "have not been set.\n" +
                                                   "Please input setting values"
                                                   " to save them.",
                                                   QtWidgets.QMessageBox.Ok,
                                                   QtWidgets.QMessageBox.Ok)
            else:
                self.__close = False

    def __save_settings_and_close(self):
        """ Save settings and close dialog.
        """
        self.__update_parameters()
        if self.__close:
            self.close()