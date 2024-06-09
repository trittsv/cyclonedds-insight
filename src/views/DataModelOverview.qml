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
import QtQuick.Dialogs

import org.eclipse.cyclonedds.insight


Rectangle {
    id: dataModelOverviewId
    implicitHeight: 350
    SplitView.minimumWidth: 50
    color: rootWindow.isDarkMode ? Constants.darkOverviewBackground : Constants.lightOverviewBackground

    Component.onCompleted: {
        datamodelRepoModel.loadModules()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        RowLayout {
            spacing: 0

            Label {
                text: "Data Model"
                Layout.leftMargin: 10
            }
            Item {
                Layout.fillWidth: true
            }

            Button {
                text: "Import"
                Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
                onClicked: {
                    console.log("Import idl files clicked")
                    idlFileDropAreaId.isEntered = true
                }
            }
            Button {
                text: "Clear"
                Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
                onClicked: {
                    console.log("Clear clicked")
                    datamodelRepoModel.clear()
                }
            }
            Button {
                text: "Test"
                Layout.alignment: Qt.AlignHCenter | Qt.AlignVCenter
                onClicked: {
                    addReadWriteTester("vehicle")
                }
            }
        }

        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: 10
            clip: true
            model: datamodelRepoModel
            delegate: Item {
                implicitWidth: dataModelOverviewId.width
                implicitHeight: nameLabel.implicitHeight * 1.5
                Label {
                    id: nameLabel
                    text: name
                }
            }
        }
    }
}