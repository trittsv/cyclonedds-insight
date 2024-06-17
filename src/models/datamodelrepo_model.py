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

from PySide6.QtCore import Qt, QModelIndex, QAbstractListModel, Qt, QByteArray, QStandardPaths, QFile, QDir, QProcess, QThread
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
from dataclasses import dataclass
import typing
import time
import datetime

from cyclonedds.core import Listener, Qos, Policy, WaitSet, ReadCondition, SampleState, ViewState, InstanceState
from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.sub import Subscriber, DataReader
from cyclonedds.util import duration


@dataclass
class DataModelItem:
    id: str
    parts: dict


class DatamodelRepoModel(QAbstractListModel):

    NameRole = Qt.UserRole + 1

    newDataArrived = Signal(str)

    def __init__(self, parent=QObject | None) -> None:
        super().__init__()
        self.dataModelItems = {}
        self.threads = {}
        self.app_data_dir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        self.datamodel_dir = os.path.join(self.app_data_dir, "datamodel")
        self.destination_folder_idl = os.path.join(self.datamodel_dir, "idl")
        self.destination_folder_py = os.path.join(self.datamodel_dir, "py")

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> typing.Any:
        if not index.isValid():
            return None
        row = index.row()
        if role == self.NameRole:
            return str(list(self.dataModelItems.keys())[row])
        elif False:
            pass

        return None

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.NameRole: b'name'
        }

    def rowCount(self, index: QModelIndex = QModelIndex()) -> int:
        return len(self.dataModelItems.keys())

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
        logging.info("add urls:" + str(urls))

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

        parent_dir = self.destination_folder_idl
        idls = [name for name in os.listdir(parent_dir) if os.path.isfile(os.path.join(parent_dir, name))]

        for idl in idls:
            print(idl)
            if True:

                destination_file = os.path.join(self.destination_folder_idl, idl)

                # Compile idl to py file
                if not QDir(self.destination_folder_py).exists():
                    QDir().mkpath(self.destination_folder_py)

                arguments = ["-l"]
                application_path = "./"

                if getattr(sys, 'frozen', False):
                    # Bundled as App - use idlc and _idlpy from app binaries
                    application_path = sys._MEIPASS
                    search_pattern = os.path.join(application_path, "_idlpy.*")
                    matching_files = glob.glob(search_pattern)
                    matching_files.sort()
                    if matching_files:
                        arguments.append(os.path.normpath(matching_files[0]))
                        logging.debug("Found _idlpy: " + matching_files[0])
                    else:
                        logging.critical("No _idlpy lib found")
                else:
                    arguments.append("py")
                    # Started as python program
                    #   - use idlc from cyclonedds_home
                    #   - use _idlpy from pip package
                    if "CYCLONEDDS_HOME" in os.environ:
                        application_path = os.environ["CYCLONEDDS_HOME"] + "/bin"

                arguments.append("-o")
                arguments.append(os.path.normpath(self.destination_folder_py))
                arguments.append(os.path.normpath(destination_file))

                command = os.path.normpath(f"{application_path}/idlc")

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
        self.dataModelItems.clear()
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
        logging.debug("")

        dir = QDir(self.destination_folder_py)
        if not dir.exists():
            return

        parent_dir = self.destination_folder_py
        sys.path.insert(0, parent_dir)

        submodules = [name for name in os.listdir(parent_dir) if os.path.isdir(os.path.join(parent_dir, name))]

        for submodule in submodules:
            module_name = submodule
            logging.debug("Inspecting "  + module_name)
            try:
                logging.debug("a")
                module = importlib.import_module(module_name)
                logging.debug("b")
                all_types = getattr(module, '__all__', [])
                for type_name in all_types:
                    logging.debug("Inspecting "  + module_name+ " " + type_name)
                    try:
                        cls = getattr(importlib.import_module(module_name), type_name)
                    except Exception as e:
                        logging.error(f"Error importing 2 {module_name} : {type_name} : {e}")
                    if inspect.isclass(cls):

                        if type_name == "T_AudioFormatType":
                            self.print_class_attributes(cls)

                        if not self.has_nested_annotation(cls) and not self.is_enum(cls):
                            logging.debug(f"Not nested !? {str(cls)}") 
                            sId: str = f"{module_name}.{cls.__name__}"
                            if sId not in self.dataModelItems:
                                self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
                                self.dataModelItems[sId] = DataModelItem(sId, [module_name, cls.__name__])
                                self.endInsertRows()

            except Exception as e:
                logging.error(f"Error importing {module_name}: {e}")

    def has_nested_annotation(self, cls):
        return 'nested' in getattr(cls, '__idl_annotations__', {})

    def is_enum(self, cls):
        return getattr(cls, '__doc__', None) == "An enumeration."


    def print_class_attributes(self, cls):
        logging.debug(f"Attributes of class {cls.__name__}:")
        for attr_name in dir(cls):
            logging.debug(f"  {attr_name}: {getattr(cls, attr_name)}")

    @Slot(int, str, str, str, str, str)
    def addReader(self, domain_id, topic_name, topic_type, q_own, q_dur, q_rel):
        print(domain_id, topic_name, topic_type, q_own, q_dur, q_rel)
        logging.debug("try add reader")

        if topic_type in self.dataModelItems:
            module_type = importlib.import_module(self.dataModelItems[topic_type].parts[0])
            class_type = getattr(module_type, self.dataModelItems[topic_type].parts[1])

            print(module_type)
            print(class_type)

            qos = Qos(
                Policy.Reliability.BestEffort,
                Policy.Deadline(duration(microseconds=10)),
                Policy.Durability.TransientLocal,
                Policy.History.KeepLast(10)
            )

            if domain_id in self.threads:
                self.threads[domain_id].receive_data(topic_name, class_type, qos)
            else:
                self.threads[domain_id] = WorkerThread(domain_id, topic_name, class_type, qos)
                self.threads[domain_id].data_emitted.connect(self.received_data)
                self.threads[domain_id].start()

        logging.debug("try add reader ... DONE")

    @Slot(str)
    def received_data(self, data: str):
        self.newDataArrived.emit(data)

    @Slot()
    def deleteAllReaders(self):
        for key in list(self.threads.keys()):
            if self.threads[key]:
                self.threads[key].stop()
                self.threads[key].wait()
        self.threads.clear()


class WorkerThread(QThread):

    data_emitted = Signal(str)
    
    def __init__(self, domain_id, topic_name, topic_type, qos, parent=None):
        super().__init__(parent)
        self.domain_id = domain_id
        self.topic_name = topic_name
        self.topic_type = topic_type
        self.qos = qos
        self.running = True
        self.readerData = []

    @Slot()
    def receive_data(self, topic_name, topic_type, qos):
        logging.info("Add reader")
        try:
            topic = Topic(self.domain_participant, topic_name, topic_type, qos=qos)
            subscriber = Subscriber(self.domain_participant)
            reader = DataReader(subscriber, topic)
            readCondition = ReadCondition(reader, SampleState.Any | ViewState.Any | InstanceState.Any)
            self.waitset.attach(readCondition)

            self.readerData.append((topic,subscriber, reader, readCondition))
        except Exception as e:
            logging.error(f"Error creating reader {topic_name}: {e}")

    def run(self):
        logging.info(f"Worker thread for domain({str(self.domain_id)}) ...")

        try:

            self.domain_participant = DomainParticipant(self.domain_id)
            self.waitset = WaitSet(self.domain_participant)

            topic = Topic(self.domain_participant, self.topic_name, self.topic_type, qos=self.qos)
            subscriber = Subscriber(self.domain_participant)
            reader = DataReader(subscriber, topic)
        
            readCondition = ReadCondition(reader, SampleState.Any | ViewState.Any | InstanceState.Any)
            self.waitset.attach(readCondition)
        
            self.readerData.append((topic,subscriber, reader, readCondition))

            while self.running:
                amount_triggered = 0
                try:
                    amount_triggered = self.waitset.wait(duration(milliseconds=100))
                except:
                    pass
                if amount_triggered == 0:
                    continue

                for (topicItem, subsItem, readItem, condItem) in self.readerData:
                    for sample in readItem.take(condition=condItem):
                        self.data_emitted.emit(f"[{str(datetime.datetime.now().isoformat())}]  -  {str(sample)}")

            logging.info(f"Worker thread for domain({str(self.domain_id)}) ... DONE")

        except Exception as e:
            logging.error(f"Error creating reader {self.topic_name}: {e}")

    def stop(self):
        logging.info(f"Request to stop worker thread for domain({str(self.domain_id)})")
        self.running = False
