/*
 * Copyright(c) 2024 Sven Trittler
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
*/

import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts

import org.eclipse.cyclonedds.insight


Rectangle {
    id: readWriteId
    color: rootWindow.isDarkMode ? Constants.darkMainContent : Constants.lightMainContent

    property int domainId: 0
    property string topicType

    Component.onCompleted: {
        console.log("ReadWriteTester", readWriteId.topicType)
    }



    Column {
        anchors.fill: parent
        spacing: 10
        padding: 10

        Label {
            text: "Create Reader or Writer"
            font.bold: true
            font.pixelSize: 30
            Layout.alignment: Qt.AlignHCenter
        }

        Label {
            text: "Topic Type"
            font.bold: true
        }
        Label {
            text: readWriteId.topicType
        }

        Label {
            text: "Topic Name"
            font.bold: true
        }
        TextField {
            id: login
            placeholderText: "Enter Topic Name"
            width: readWriteId.width - 20
        }

        Label {
            text: "Ownership"
            font.bold: true
        }
        ComboBox {
            model: ["DDS_OWNERSHIP_SHARED", "DDS_OWNERSHIP_EXCLUSIVE"]
            width: readWriteId.width - 20
        }

        Label {
            text: "Durability"
            font.bold: true
        }
        ComboBox {
            model: ["DDS_DURABILITY_VOLATILE", "DDS_DURABILITY_TRANSIENT_LOCAL", "DDS_DURABILITY_TRANSIENT", "DDS_DURABILITY_PERSISTENT"]
            width: readWriteId.width - 20
        }

        Label {
            text: "Reliability"
            font.bold: true
        }
        ComboBox {
            model: ["DDS_RELIABILITY_BEST_EFFORT", "DDS_RELIABILITY_RELIABLE"]
            width: readWriteId.width - 20
        }

        Row {
            Button {
                text: qsTr("Create Reader")
                onClicked: {

                }
            }
            Button {
                text: qsTr("Create Writer")
                onClicked: {

                }
            }
            /*Button {
                text: qsTr("Cancel")
                onClicked: {

                }
            }*/
        }
    }

}
