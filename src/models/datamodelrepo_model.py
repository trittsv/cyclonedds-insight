"""
 * Copyright(c) 2024 Sven Trittler
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
"""

from PySide6.QtCore import Qt, QModelIndex, QAbstractListModel, Qt, QByteArray, QStandardPaths, QFile, QDir, QProcess
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QApplication, QTreeView
from PySide6.QtQuick import QQuickView
from PySide6.QtCore import QObject, Signal, Property, Slot
import logging
import os
import sys
import importlib
import inspect
import subprocess
import glob
import dds_data
from dds_qos import dds_qos_policy_id

import typing



class DatamodelRepoModel(QAbstractListModel):

    NameRole = Qt.UserRole + 1

    def __init__(self, parent=QObject | None) -> None:
        super().__init__()
        self._studend_list = []
        self.app_data_dir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        self.datamodel_dir = os.path.join(self.app_data_dir, "datamodel")
        self.destination_folder_idl = os.path.join(self.datamodel_dir, "idl")
        self.destination_folder_py = os.path.join(self.datamodel_dir, "py")

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> typing.Any:
        if not index.isValid():
            return None
        row = index.row()
        if role == self.NameRole:
            return ".".join(self._studend_list[row])
        elif False:
            pass

        return None

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.NameRole: b'name'
        }

    def rowCount(self, index: QModelIndex = QModelIndex()) -> int:
        return len(self._studend_list)

    def add_student(self, student: str) -> None:
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        self._studend_list.append((student,student))
        self.endInsertRows()




    def execute_command(self, command, cwd):
        logging.debug("start executing command ...")
        try:
            # Run the command and capture stdout, stderr
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, cwd=cwd)
            stdout, stderr = process.communicate()
            logging.debug("command executed, eval result.")

            # Check if there was an error
            if process.returncode != 0:
                logging.debug("Error occurred:")
                logging.debug(stdout.decode("utf-8"))
                logging.debug(stderr.decode("utf-8"))
                return None

            logging.debug("Command Done,")
            logging.debug(stdout.decode("utf-8"))
            logging.debug(stderr.decode("utf-8"))

        except Exception as e:
            logging.debug("An error occurred:", e)

    @Slot(list)
    def addUrls(self, urls):
        print("add urls:", urls)
        for url in urls:
            if url.isLocalFile():

                # Copy idl source file
                source_file = url.toLocalFile()
                logging.debug("IDL-Folder: " + self.destination_folder_idl)
                if not QDir(self.destination_folder_idl).exists():
                    QDir().mkpath(self.destination_folder_idl)

                destination_file = os.path.join(self.destination_folder_idl, os.path.basename(source_file))

                if (QFile.exists(destination_file)):
                    QFile.remove(destination_file)

                if QFile.copy(source_file, destination_file):
                    logging.debug("File copied successfully. " + os.path.basename(source_file))
                else:
                    logging.error("Failed to copy file.")
                    break

                # Compile idl to py file
                if not QDir(self.destination_folder_py).exists():
                    QDir().mkpath(self.destination_folder_py)

                arguments = ["-l", "py"]
                application_path = "./"

                if getattr(sys, 'frozen', False):
                    # Bundled as App - use idlc and _idlpy from app binaries
                    application_path = sys._MEIPASS
                    search_pattern = os.path.join(application_path, "_idlpy.*")
                    matching_files = glob.glob(search_pattern)
                    matching_files.sort()
                    if matching_files:
                        arguments.append("-y")
                        arguments.append(matching_files[0])
                        logging.debug("Found _idlpy: " + matching_files[0])
                    else:
                        logging.warn("No _idlpy lib found")
                else:
                    # Started as python program
                    #   - use idlc from cyclonedds_home
                    #   - use _idlpy from pip package
                    if "CYCLONEDDS_HOME" in os.environ:
                        application_path = os.environ["CYCLONEDDS_HOME"] + "/bin"

                arguments.append("-o")
                arguments.append(self.destination_folder_py)
                arguments.append(destination_file)

                command = f"{application_path}/idlc"

                logging.info("Execute: " + command + " " + " ".join(arguments))

                process = QProcess()
                process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
                process.setWorkingDirectory(self.destination_folder_py)
                process.start(command, arguments)

                if process.waitForFinished():
                    if process.exitStatus() == QProcess.NormalExit:
                        logging.debug(str(process.readAll()))
                        logging.debug("Process finished successfully.") 
                    else:
                        logging.debug("Process failed with error code: " + str(process.exitCode()))
                else:
                    logging.debug("Failed to start process:" + str(process.errorString()))

        self.loadModules()

    @Slot()
    def clear(self):
        self.beginResetModel()
        self.delete_folder(self.datamodel_dir)
        self._studend_list.clear()
        self.endResetModel()

    def delete_folder(self, folder_path):
        dir = QDir(folder_path)
        if dir.exists():
            success = dir.removeRecursively()
            if success:
                print(f"Successfully deleted folder: {folder_path}")
            else:
                print(f"Failed to delete folder: {folder_path}")
        else:
            print(f"Folder does not exist: {folder_path}")

    @Slot()
    def loadModules(self):
        #self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        #self._studend_list.append(source_file)
        #self.endInsertRows()

        parent_dir = self.destination_folder_py
        sys.path.insert(0, parent_dir)

        submodules = [name for name in os.listdir(parent_dir) if os.path.isdir(os.path.join(parent_dir, name))]

        for submodule in submodules:
            module_name = submodule
            try:
                module = importlib.import_module(module_name)
                all_types = getattr(module, '__all__', [])
                for type_name in all_types:
                    cls = getattr(importlib.import_module(module_name), type_name)
                    if inspect.isclass(cls):
                        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
                        self._studend_list.append((module_name, cls.__name__))
                        self.endInsertRows()

            except Exception as e:
                print(f"Error importing {module_name}: {e}")

