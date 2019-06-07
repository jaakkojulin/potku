# coding=utf-8
"""
Created on 23.4.2018
Updated on 29.8.2018

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
__author__ = "Severi Jääskeläinen \n Samuel Kaiponen \n Heta Rekilä \n " \
             "Sinikka Siironen"
__version__ = "2.0"

import modules.masses as masses
import os
import platform

from dialogs.element_selection import ElementSelectionDialog

from modules.general_functions import set_input_field_red

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5 import uic


class RecoilElementSelectionDialog(QtWidgets.QDialog):
    """Selection Settings dialog handles showing settings for selection made in
    measurement (in matplotlib graph).
    """

    def __init__(self, recoil_atom_distribution):
        """Inits simulation element selection dialog.
        """
        super().__init__()
        self.ui = uic.loadUi(
            os.path.join("ui_files", "ui_recoil_element_selection_dialog.ui"),
            self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.recoil_atom_distribution = recoil_atom_distribution

        self.element = None
        self.isotope = None
        self.color = None
        self.tmp_element = None
        self.colormap = self.recoil_atom_distribution.colormap

        # Setup connections
        self.ui.element_button.clicked.connect(self.__change_element)
        self.ui.isotope_radio.toggled.connect(self.__toggle_isotope)

        self.ui.OKButton.clicked.connect(self.__accept_settings)
        self.ui.cancelButton.clicked.connect(self.close)
        self.ui.colorPushButton.clicked.connect(self.__change_color)

        self.ui.isotopeInfoLabel.setVisible(False)

        self.isOk = False

        if platform.system() == "Darwin":
            self.ui.isotope_combobox.setFixedHeight(23)

        if platform.system() == "Linux":
            self.setMinimumWidth(350)
        self.exec_()

    def __set_color_button_color(self, element):
        """Set default color of element to color button.

        Args:
            element: String representing element.
        """
        self.ui.colorPushButton.setEnabled(True)
        if element and element != "Select":
            self.color = QtGui.QColor(self.colormap[element])
            self.__change_color_button_color(element)

    def __change_color(self):
        """
        Change the color of the recoil element.
        """
        dialog = QtWidgets.QColorDialog(self)
        color = dialog.getColor(QtGui.QColor(self.color))
        if color.isValid():
            self.color = color
            self.__change_color_button_color(self.tmp_element)

    def __change_color_button_color(self, element):
        """
        Change color button's color.

        Args:
            element: String representing element name.
        """
        text_color = "black"
        luminance = 0.2126 * self.color.red() + 0.7152 * self.color.green()
        luminance += 0.0722 * self.color.blue()
        if luminance < 50:
            text_color = "white"
        style = "background-color: {0}; color: {1};".format(self.color.name(),
                                                            text_color)
        self.ui.colorPushButton.setStyleSheet(style)

        if self.color.name() == self.colormap[element]:
            self.ui.colorPushButton.setText("Automatic [{0}]".format(element))
        else:
            self.ui.colorPushButton.setText("")

    def __change_element(self):
        """Shows dialog to change selection element.
        """
        dialog = ElementSelectionDialog()
        # Only disable these once, not if you cancel after selecting once.
        if self.ui.element_button.text() == "Select":
            self.ui.isotope_radio.setEnabled(False)
            self.ui.standard_mass_radio.setEnabled(False)
            self.ui.standard_mass_label.setEnabled(False)
        # If element was selected, proceed to enable appropriate fields.
        if dialog.element:
            self.ui.element_button.setText(dialog.element)
            self.__enable_element_fields(dialog.element)
            self.__set_color_button_color(dialog.element)
            self.tmp_element = dialog.element

            if self.ui.isotope_combobox.count() == 0:
                self.ui.isotopeInfoLabel.setVisible(True)
                set_input_field_red(self.ui.isotope_combobox)
                self.setMinimumHeight(243)
            else:
                self.ui.isotopeInfoLabel.setVisible(False)
                self.ui.isotope_combobox.setStyleSheet(
                    "background-color: %s" % "None")
                self.setMinimumHeight(200)

            self.__check_if_settings_ok()

    def __enable_element_fields(self, element):
        """Enable element information fields.

        Args:
            element: String representing element.
        """
        if element:
            self.ui.isotope_radio.setEnabled(True)
            self.ui.standard_mass_radio.setEnabled(True)
            self.ui.standard_mass_label.setEnabled(True)
            self.__load_isotopes(element)

    def __load_isotopes(self, element, current_isotope=None):
        """Change isotope information regarding element

        Args:
            element: String representing element.
            current_isotope: String representing current isotope.
        """
        standard_mass = masses.get_standard_isotope(element)
        self.ui.standard_mass_label.setText(str(round(standard_mass, 3)))
        masses.load_isotopes(element, self.ui.isotope_combobox, current_isotope)

    def __toggle_isotope(self):
        """Toggle Sample isotope radio button.
        """
        self.ui.isotope_combobox.setEnabled(self.ui.isotope_radio.isChecked())

    def __check_if_settings_ok(self):
        """Check if sample settings are ok, and enable ok button.
        """
        element = self.ui.element_button.text()
        if element:
            self.ui.OKButton.setEnabled(True)
        else:
            self.ui.OKButton.setEnabled(False)
        if self.ui.isotopeInfoLabel.isVisible():
            self.ui.OKButton.setEnabled(False)

    def __accept_settings(self):
        """Accept settings given in the selection dialog and save these to
        parent.
        """
        self.element = self.ui.element_button.text()

        # For standard isotopes:

        # Check if specific isotope was chosen and use that instead.
        if self.ui.isotope_radio.isChecked():
            isotope_index = self.ui.isotope_combobox.currentIndex()
            isotope_data = self.ui.isotope_combobox.itemData(isotope_index)
            self.isotope = isotope_data[0]

        self.isOk = True
        self.close()