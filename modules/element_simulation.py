# coding=utf-8
"""
Created on 25.4.2018
Updated on 20.6.2018

Potku is a graphical user interface for analyzation and
visualization of measurement data collected from a ToF-ERD
telescope. For physics calculations Potku uses external
analyzation components.
Copyright (C) 2018 Severi Jääskeläinen, Samuel Kaiponen, Heta Rekilä and
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
__author__ = "Severi Jääskeläinen \n Samuel Kaiponen \n Heta Rekilä \n" \
             "Sinikka Siironen"
__version__ = "2.0"

import platform
import json
import os
import math
import time

from widgets.matplotlib.simulation.recoil_atom_distribution import RecoilElement
from widgets.matplotlib.simulation.recoil_atom_distribution import Point

from modules.element import Element
from modules.mcerd import MCERD
from modules.get_espe import GetEspe
from modules.foil import CircularFoil

from modules.general_functions import rename_file


class ElementSimulation:
    """
    Class for handling the element specific simulation. Can have multiple
    MCERD objects, but only one GetEspe object.
    """

    __slots__ = "directory", "request", "name_prefix", "modification_time", \
                "simulation_type", "number_of_ions", "number_of_preions", \
                "number_of_scaling_ions", "number_of_recoils", \
                "minimum_scattering_angle", "minimum_main_scattering_angle", \
                "minimum_energy", "simulation_mode", "seed_number", \
                "recoil_elements", "recoil_atoms", "mcerd_objects", \
                "get_espe", "channel_width", "target", "detector", \
                "__mcerd_command", "__process", "settings", "espe_settings", \
                "description", "run", "spectra", "name", \
                "use_default_settings", "sample"

    def __init__(self, directory, request, recoil_elements, name_prefix="",
                 target=None, detector=None, run=None, name="Default",
                 description="", modification_time=None,
                 simulation_type="ERD", number_of_ions=1000000,
                 number_of_preions=100000, number_of_scaling_ions=5,
                 number_of_recoils=10, minimum_scattering_angle=0.05,
                 minimum_main_scattering_angle=20, simulation_mode="narrow",
                 seed_number=101, minimum_energy=1.0, channel_width=0.1,
                 use_default_settings=True, sample=None):
        """ Initializes ElementSimulation.
        Args:
            directory: Folder of simulation that contains the ElementSimulation.
            request: Request object reference.
            recoil_elements: List of RecoilElement objects.
            name_prefix: Prefix of the name, e.g. 55Mn
            target: Target object reference.
            detector: Detector object reference.
            run: Run object reference.
            name: Name of the element simulation.
            description: Description of the ElementSimulation
            modification_time: Modification time in Unix time.
            simulation_type: Type of simulation
            number_of_ions: Number of ions to be simulated.
            number_of_preions: Number of ions in presimulation.
            number_of_scaling_ions: Number of scaling ions.
            number_of_recoils: Number of recoils.
            minimum_scattering_angle: Minimum angle of scattering.
            minimum_main_scattering_angle: Minimum main angle of scattering.
            simulation_mode: Mode of simulation.
            seed_number: Seed number to give unique value to one simulation.
            minimum_energy: Minimum energy.
            channel_width: Channel width.
            sample: Sample object under which Element Simualtion belongs.
        """
        self.directory = directory
        self.request = request
        self.name_prefix = name_prefix
        self.name = name
        self.description = description
        if not modification_time:
            modification_time = time.time()
        self.modification_time = modification_time

        self.sample = sample

        # TODO RecoilAtomDistributionWidget should use the selected
        # RecoilElement.
        # Now ElementSimulation never has multiple recoil elements, only
        # recoil_elements[0] is used. In the future, ElementSimulation should
        # hold all recoil elements (= distributions) that are related to the
        # simulation (e.g. .mcsimu and .erd files).
        self.recoil_elements = recoil_elements
        self.target = target
        if detector:
            self.detector = detector
        else:
            self.detector = self.request.default_detector
        self.run = run
        self.simulation_type = simulation_type

        self.simulation_mode = simulation_mode
        self.number_of_ions = number_of_ions
        self.number_of_preions = number_of_preions
        self.number_of_scaling_ions = number_of_scaling_ions
        self.number_of_recoils = number_of_recoils
        self.minimum_scattering_angle = minimum_scattering_angle
        self.minimum_main_scattering_angle = minimum_main_scattering_angle
        self.minimum_energy = minimum_energy
        self.seed_number = seed_number
        self.channel_width = channel_width

        self.use_default_settings = use_default_settings

        if self.name_prefix != "":
            name = self.name_prefix + "-" + self.name
            prefix = self.name_prefix
        else:
            name = self.name
            if os.sep + "Default" in self.directory:
                prefix = self.name + "_element"
            else:
                prefix = self.name_prefix
        self.mcsimu_to_file(os.path.join(self.directory,
                                          name + ".mcsimu"))
        self.recoil_to_file(self.directory)
        self.profile_to_file(os.path.join(self.directory,
                                          prefix +
                                          ".profile"))

        self.__mcerd_command = os.path.join(
            "external", "Potku-bin", "mcerd" +
            (".exe" if platform.system() == "Windows" else ""))
        self.__process = None
        # This has all the mcerd objects so get_espe knows all the element
        # simulations that belong together (with different seed numbers)
        self.mcerd_objects = {}
        self.settings = None
        self.get_espe = None
        self.espe_settings = None
        self.spectra = []

    def unlock_edit(self, recoil_element):
        """
        Unlock full edit.

        Args:
            recoil_element: RecoilElement object.
        """
        recoil_element.unlock_edit()

    def get_edit_lock_on(self, recoil_element):
        """
        Get whether full edit lck is on or not.

        Args:
            recoil_element: A RecoilElement object.

        Return:
            True of False.
        """
        return recoil_element.get_edit_lock_on()

    def get_points(self, recoil_element):
        """
        Get recoile elemnt points.

        Args:
            recoil_element: A RecoilElement object.

        Return:
            Points list.
        """
        return recoil_element.get_points()

    def get_xs(self, recoil_element):
        """
        Get x coordinates of a RecoilElement.

        Args:
            recoil_element: A RecoilElement object.

        Return:
            X coordinates in a list.
        """
        return recoil_element.get_xs(),

    def get_ys(self, recoil_element):
        """
        Get y coordinates of a RecoilElement.

        Args:
            recoil_element: A RecoilElement object.

        Return:
            Y coodinates in a list.
        """
        return recoil_element.get_ys(),

    def get_left_neighbor(self, recoil_element, point):
        """
        Get point's left neighbour.

        Args:
             recoil_element: A RecoilElement object.
             point: A Point object.

        Return:
            A point.
        """
        return recoil_element.get_left_neighbor(point)

    def get_right_neighbor(self, recoil_element, point):
        """
        Get point's right neighbour.

        Args:
             recoil_element: A RecoilElement object.
             point: A Point object.

        Return:
            A point.
        """
        return recoil_element.get_right_neighbor(point)

    def get_point_by_i(self, recoil_element, i):
        """
        Get a point by index.

        Args:
            recoil_element: A RecoilElement object.
            i: Index.

        Return:
            A point.
        """
        return recoil_element.get_point_by_i(i)

    def add_point(self, recoil_element, new_point):
        """
        Add a new point to recoil element.

        Args:
             recoil_element: A RecoilElement object.
             new_point: Point to be added.
        """
        recoil_element.add_point(new_point)

    def remove_point(self, recoil_element, point):
        """
        Remove a point from recoil element.

        Args:
            recoil_element: A RecoilElement object.
            point: Point to be removed.
        """
        recoil_element.remove_point(point)

    def update_recoil_element(self, recoil_element, new_values):
        """Updates RecoilElement object with new values.

        Args:
            recoil_element: RecoilElement object to update.
            new_values: New values as a dictionary.
        """
        old_name = recoil_element.name
        try:
            recoil_element.name = new_values["name"]
            recoil_element.description = new_values["description"]
            recoil_element.reference_density = new_values["reference_density"]
        except KeyError:
            raise
        # Delete possible extra rec files.
        filename_to_delete = ""
        for file in os.listdir(self.directory):
            if file.startswith(recoil_element.prefix) and file.endswith(".rec"):
                filename_to_delete = file
                break
        if filename_to_delete:
            os.remove(os.path.join(self.directory, filename_to_delete))

        self.recoil_to_file(self.directory)

        if old_name != recoil_element.name:
            recoil_file = os.path.join(self.directory, recoil_element.prefix
                                       + "-" + old_name + ".recoil")
            if os.path.exists(recoil_file):
                new_name = recoil_element.prefix + "-" + recoil_element.name \
                           + ".recoil"
                rename_file(recoil_file, new_name)

            erd_file = os.path.join(self.directory, recoil_element.prefix +
                                    "-" + old_name + "." + str(self.seed_number)
                                    + ".erd")
            if os.path.exists(erd_file):
                new_name = recoil_element.prefix + "-" + recoil_element.name \
                           + "." + str(self.seed_number) + ".erd"
                rename_file(erd_file, new_name)

            simu_file = os.path.join(self.directory, recoil_element.prefix +
                                     "-" + old_name + ".simu")
            if os.path.exists(simu_file):
                new_name = recoil_element.prefix + "-" + recoil_element.name \
                           + ".simu"
                rename_file(simu_file, new_name)

    def calculate_solid(self):
        """
        Calculate the solid parameter.
        Return:
            Returns the solid parameter calculated.
        """
        transmissions = self.detector.foils[0].transmission
        for f in self.detector.foils:
            transmissions *= f.transmission

        smallest_solid_angle = self.calculate_smallest_solid_angle()

        return smallest_solid_angle * transmissions

    def calculate_smallest_solid_angle(self):
        """
        Calculate the smallest solid angle.
        Return:
            Smallest solid angle. (unit millisteradian)
        """
        foil = self.detector.foils[0]
        try:
            if type(foil) is CircularFoil:
                radius = foil.diameter / 2
                smallest = math.pi * radius ** 2 / foil.distance ** 2
            else:
                smallest = foil.size[0] * foil.size[1] / foil.distance ** 2
            i = 1
            while i in range(len(self.detector.foils)):
                foil = self.detector.foils[i]
                if type(foil) is CircularFoil:
                    radius = foil.diameter / 2
                    solid_angle = math.pi * radius ** 2 / foil.distance ** 2
                else:
                    solid_angle = foil.size[0] * foil.size[
                        1] / foil.distance ** 2
                    pass
                if smallest > solid_angle:
                    smallest = solid_angle
                i += 1
            return smallest * 1000  # usually the unit is millisteradian,
            # hence the multiplication by 1000
        except ZeroDivisionError:
            return 0

    @classmethod
    def from_file(cls, request, prefix, simulation_folder, mcsimu_file_path,
                  profile_file_path):
        """Initialize ElementSimulation from JSON files.

        Args:
            request: Request that ElementSimulation belongs to.
            prefix: String that is used to prefix ".rec" files of this
            ElementSimulation.
            simulation_folder: A file path to simulation folder that contains
            files ending with ".rec".
            mcsimu_file_path: A file path to JSON file containing the
            simulation parameters.
            profile_file_path: A file path to JSON file containing the
            channel width.
        """

        obj = json.load(open(mcsimu_file_path))

        use_default_settings_str = obj["use_default_settings"]
        if use_default_settings_str == "True":
            use_default_settings = True
        else:
            use_default_settings = False
        try:
            name_prefix, name = obj["name"].split("-")
        except ValueError as e:
            name = obj["name"]
            name_prefix = ""

        description = obj["description"]
        modification_time = obj["modification_time_unix"]
        simulation_type = obj["simulation_type"]
        simulation_mode = obj["simulation_mode"]
        number_of_ions = obj["number_of_ions"]
        number_of_preions = obj["number_of_preions"]
        seed_number = obj["seed_number"]
        number_of_recoils = obj["number_of_recoils"]
        number_of_scaling_ions = obj["number_of_scaling_ions"]
        minimum_scattering_angle = obj["minimum_scattering_angle"]
        minimum_main_scattering_angle = obj["minimum_main_scattering_angle"]
        minimum_energy = obj["minimum_energy"]

        # Read channel width from .profile file.
        obj = json.load(open(profile_file_path))
        channel_width = obj["energy_spectra"]["channel_width"]

        # Read .rec files from simulation folder
        recoil_elements = []
        for file in os.listdir(simulation_folder):
            if file.startswith(prefix) and file.endswith(".rec"):
                obj = json.load(open(os.path.join(simulation_folder, file)))
                points = []
                for dictionary_point in obj["profile"]:
                    x, y = dictionary_point["Point"].split(" ")
                    points.append(Point((float(x), float(y))))
                element = RecoilElement(Element.from_string(obj["element"]),
                                        points)
                element.name = obj["name"]
                element.description = obj["description"]
                element.reference_density = obj["reference_density"] / 1e22
                element.simulation_type = obj["simulation_type"]

                element.modification_time = obj["modification_time_unix"]

                element.channel_width = channel_width
                recoil_elements.append(element)
                # TODO For now, reading just the first matching .rec file.
                # All .rec files that belong to this ElementSimulation should
                #  be read and RecoilElement objects created from them.
                break

        return cls(simulation_folder, request, recoil_elements,
                   name_prefix=name_prefix,
                   description=description,
                   simulation_type=simulation_type,
                   modification_time=modification_time, name=name,
                   number_of_ions=number_of_ions,
                   number_of_preions=number_of_preions,
                   number_of_scaling_ions=number_of_scaling_ions,
                   number_of_recoils=number_of_recoils,
                   minimum_scattering_angle=minimum_scattering_angle,
                   minimum_main_scattering_angle=minimum_main_scattering_angle,
                   simulation_mode=simulation_mode,
                   seed_number=seed_number,
                   minimum_energy=minimum_energy,
                   use_default_settings=use_default_settings,
                   channel_width=channel_width)

    def mcsimu_to_file(self, file_path):
        """Save mcsimu settings to file.

        Args:
            file_path: File in which the mcsimu settings will be saved.
        """
        if self.name_prefix != "":
            name = self.name_prefix + "-" + self.name
        else:
            name = self.name
        if not self.use_default_settings:
            obj = {
                "name": name,
                "description": self.description,
                "modification_time": time.strftime("%c %z %Z", time.localtime(
                    time.time())),
                "modification_time_unix": time.time(),
                "simulation_type": self.simulation_type,
                "simulation_mode": self.simulation_mode,
                "number_of_ions": self.number_of_ions,
                "number_of_preions": self.number_of_preions,
                "seed_number": self.seed_number,
                "number_of_recoils": self.number_of_recoils,
                "number_of_scaling_ions": self.number_of_scaling_ions,
                "minimum_scattering_angle": self.minimum_scattering_angle,
                "minimum_main_scattering_angle": self.minimum_main_scattering_angle,
                "minimum_energy": self.minimum_energy,
                "use_default_settings": str(self.use_default_settings)
            }
        else:
            elem_sim = self.request.default_element_simulation
            obj = {
                "name": name,
                "description": elem_sim.description,
                "modification_time": time.strftime("%c %z %Z", time.localtime(
                    time.time())),
                "modification_time_unix": time.time(),
                "simulation_type": elem_sim.simulation_type,
                "simulation_mode": elem_sim.simulation_mode,
                "number_of_ions": elem_sim.number_of_ions,
                "number_of_preions": elem_sim.number_of_preions,
                "seed_number": elem_sim.seed_number,
                "number_of_recoils": elem_sim.number_of_recoils,
                "number_of_scaling_ions": elem_sim.number_of_scaling_ions,
                "minimum_scattering_angle": elem_sim.minimum_scattering_angle,
                "minimum_main_scattering_angle": elem_sim.minimum_main_scattering_angle,
                "minimum_energy": elem_sim.minimum_energy,
                "use_default_settings": str(self.use_default_settings)
            }

        with open(file_path, "w") as file:
            json.dump(obj, file, indent=4)

    def recoil_to_file(self, simulation_folder):
        """Save recoil settings to file.

        Args:
            simulation_folder: Path to simulation folder in which ".rec"
            files are stored.
        """
        for recoil_element in self.recoil_elements:
            recoil_file = os.path.join(simulation_folder,
                                       recoil_element.prefix + "-" +
                                       recoil_element.name + ".rec")
            if recoil_element.element.isotope:
                element_str = "{0}{1}".format(recoil_element.element.isotope,
                                              recoil_element.element.symbol)
            else:
                element_str = recoil_element.element.symbol

            obj = {
                "name": recoil_element.name,
                "description": recoil_element.description,
                "modification_time": time.strftime("%c %z %Z", time.localtime(
                    time.time())),
                "modification_time_unix": time.time(),
                "simulation_type": recoil_element.type,
                "element": element_str,
                "reference_density": recoil_element.reference_density * 1e22,
                "profile": []
            }

            for point in recoil_element.get_points():
                point_obj = {
                    "Point": str(round(point.get_x(), 2)) + " " + str(round(
                        point.get_y(), 4))
                }
                obj["profile"].append(point_obj)

            with open(recoil_file, "w") as file:
                json.dump(obj, file, indent=4)

    def profile_to_file(self, file_path):
        """Save profile settings (only channel width) to file.

        Args:
            file_path: File in which the channel width will be saved.
        """
        # Read .profile to obj to update only channel width
        if os.path.exists(file_path):
            obj_profile = json.load(open(file_path))
            obj_profile["modification_time"] = time.strftime("%c %z %Z",
                                                             time.localtime(
                                                                 time.time()))
            obj_profile["modification_time_unix"] = time.time()
            obj_profile["energy_spectra"]["channel_width"] = self.channel_width
        else:
            obj_profile = {"energy_spectra": {}}
            obj_profile["modification_time"] = time.strftime("%c %z %Z",
                                                             time.localtime(
                                                                 time.time()))
            obj_profile["modification_time_unix"] = time.time()
            obj_profile["energy_spectra"]["channel_width"] = self.channel_width

        with open(file_path, "w") as file:
            json.dump(obj_profile, file, indent=4)

    def start(self):
        """ Start the simulation."""
        if self.run is None:
            run = self.request.default_run
        else:
            run = self.run
        if self.use_default_settings:
            elem_sim = self.request.default_element_simulation
        else:
            elem_sim = self
        if self.detector is None:
            detector = self.request.default_detector
        else:
            detector = self.detector
        self.settings = {
            "simulation_type": elem_sim.simulation_type,
            "number_of_ions": elem_sim.number_of_ions,
            "number_of_ions_in_presimu": elem_sim.number_of_preions,
            "number_of_scaling_ions": elem_sim.number_of_scaling_ions,
            "number_of_recoils": elem_sim.number_of_recoils,
            "minimum_scattering_angle": elem_sim.minimum_scattering_angle,
            "minimum_main_scattering_angle": elem_sim.minimum_main_scattering_angle,
            "minimum_energy_of_ions": elem_sim.minimum_energy,
            "simulation_mode": elem_sim.simulation_mode,
            "seed_number": elem_sim.seed_number,
            "beam": run.beam,
            "target": self.target,
            "detector": detector,
            "recoil_element": self.recoil_elements[0]
        }
        self.mcerd_objects[elem_sim.seed_number] = MCERD(self.settings)

    def stop(self):
        """ Stop the simulation."""
        for sim in list(self.mcerd_objects.keys()):
            self.mcerd_objects[sim].stop_process()
            try:
                self.mcerd_objects[sim].copy_result(self.directory)
            except FileNotFoundError:
                raise
            del (self.mcerd_objects[sim])

    def pause(self):
        """Pause the simulation."""
        # TODO: Implement this sometime in the future.
        pass

    def calculate_espe(self):
        """
        Calculate the energy spectrum from the MCERD result file.
        """
        recoil_file = os.path.join(self.directory,
                                   self.recoil_elements[0].prefix + "-" +
                                   self.recoil_elements[0].name +
                                   ".recoil")
        self.recoil_elements[0].write_recoil_file(recoil_file)

        if self.run is None:
            run = self.request.default_run
        else:
            run = self.run
        if self.use_default_settings:
            seed_number = self.request.default_element_simulation.seed_number
        else:
            seed_number = self.seed_number
        if self.detector is None:
            detector = self.request.default_detector
        else:
            detector = self.detector
        self.espe_settings = {
            "beam": run.beam,
            "detector": detector,
            "target": self.target,
            "ch": self.channel_width,
            "reference_density": self.recoil_elements[0].reference_density,
            "fluence": run.fluence,
            "timeres": detector.timeres,
            "solid": self.calculate_solid(),
            "erd_file": os.path.join(self.directory,
                                     self.recoil_elements[0].prefix + "-" +
                                     self.recoil_elements[0].name + ".*.erd"),
            "spectrum_file": os.path.join(self.directory,
                                          self.recoil_elements[0].prefix + "-" +
                                          self.recoil_elements[0].name +
                                          ".simu"),
            "recoil_file": recoil_file
        }
        self.get_espe = GetEspe(self.espe_settings)
