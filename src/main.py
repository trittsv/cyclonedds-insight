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

import sys
import os

# Execution before first import of cyclonedds
if getattr(sys, 'frozen', False):
    APPLICATION_PATH = sys._MEIPASS
    # remove the env variable early to ensure that
    # cyclonedds-python will pick the correct libs
    # provided by the app bundle
    if "CYCLONEDDS_HOME" in os.environ:
        del os.environ["CYCLONEDDS_HOME"]
else:
    APPLICATION_PATH = os.path.dirname(os.path.abspath(__file__))

    # CycloneDDS
    cyclonedds_home = os.getenv('CYCLONEDDS_HOME')
    if not cyclonedds_home:
        raise Exception('CYCLONEDDS_HOME environment variable is not set.')
    else:
        print('cyclonedds_home: ' + cyclonedds_home)

    # CycloneDDS-Python
    cyclonedds_python_home = os.getenv('CYCLONEDDS_PYTHON_HOME')
    if not cyclonedds_python_home:
        raise Exception('CYCLONEDDS_PYTHON_HOME environment variable is not set - must be install via pip install -e .')
    else:
        print('cyclonedds_python_home: ' + cyclonedds_python_home)

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PySide6.QtCore import qInstallMessageHandler, QUrl
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtQuickControls2 import QQuickStyle
import logging
import dds_data
from models.overview_model import TreeModel, TreeNode
from models.endpoint_model import EndpointModel
from models.datamodel_model import DatamodelModel
from utils import qt_message_handler, setupLogger

# generated by pyside6-rcc
import qrc_file 


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    app.setWindowIcon(QIcon(QPixmap(":/res/images/cyclonedds.png")))
    app.setApplicationName("CycloneDDS Insight")
    app.setApplicationDisplayName("CycloneDDS Insight")
    app.setOrganizationName("cyclonedds")
    app.setOrganizationDomain("org.eclipse.cyclonedds.insight")

    # Setup the logger
    setupLogger(logging.DEBUG)

    # Print qml log messages into the python log
    qInstallMessageHandler(qt_message_handler)

    logging.info("Starting App ...")
    logging.debug(f"Application path: {APPLICATION_PATH}")

    if sys.platform == "darwin":
        QQuickStyle.setStyle("macOS")
    else:
        QQuickStyle.setStyle("Fusion")

    data = dds_data.DdsData()
    rootItem = TreeNode("Root")
    treeModel = TreeModel(rootItem)
    datamodelRepoModel = DatamodelModel()

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("treeModel", treeModel)
    engine.rootContext().setContextProperty("datamodelRepoModel", datamodelRepoModel)
    engine.rootContext().setContextProperty("CYCLONEDDS_URI", os.getenv("CYCLONEDDS_URI", "<not set>"))
    qmlRegisterType(EndpointModel, "org.eclipse.cyclonedds.insight", 1, 0, "EndpointModel")

    engine.load(QUrl("qrc:/src/views/main.qml"))
    if not engine.rootObjects():
        logging.critical("Failed to load qml")
        sys.exit(-1)

    # Add default domain
    data.add_domain(0)

    logging.info("qt ...")
    ret_code = app.exec()
    logging.info("qt ... DONE")

    # Clean up threads
    datamodelRepoModel.deleteAllReaders()
    data.join_observer()

    sys.exit(ret_code)
