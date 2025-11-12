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
import "qrc:/src/views"


Window {
    id: atcWindowId
    title: "ATC Demo"
    width: 800
    minimumWidth: 400
    height: 450
    minimumHeight: 400
    flags: Qt.Window
    property var shapesMap
    property var pendingWriterMap
    property var triangleScale: 0.7
    property bool paused: false

    ListModel {
        id: partitionsModel
    }

    function updatePartitions() {
        atcMap.clearAirplanes()
        var partitions = []
        for (var i = 0; i < partitionsModel.count; i++) {
            partitions.push(partitionsModel.get(i).text)
        }
        atcModel.restart(partitions)
    }

    Rectangle {
        id: background
        anchors.fill: parent
        color: rootWindow.isDarkMode ? Constants.darkOverviewBackground : Constants.lightOverviewBackground

        RowLayout {
            anchors.fill: parent
            spacing: 5

            ColumnLayout {
                id: leftColumnOverview
                Layout.preferredWidth: 250
                Layout.maximumWidth: 250
                Layout.fillHeight: true

                Label {
                    id: titleLabel
                    text: "Air Traffic Control Demo"
                    font.bold: true
                    leftPadding: 5
                }

                Label {
                    text: "Examples:"
                    leftPadding: 5
                }

                TextInput {
                    text: "/*"
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextInput.NoWrap
                    Layout.fillWidth: true
                    leftPadding: 10
                    color: titleLabel.color
                }

                TextInput {
                    text: "/Europe/*"
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextInput.NoWrap
                    Layout.fillWidth: true
                    leftPadding: 10
                    color: titleLabel.color
                }

                TextInput {
                    text: "/Ocean/*"
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextInput.NoWrap
                    Layout.fillWidth: true
                    leftPadding: 10
                    color: titleLabel.color
                }

                TextInput {
                    text: "/Europe/Germany"
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextInput.NoWrap
                    Layout.fillWidth: true
                    leftPadding: 10
                    color: titleLabel.color
                }

                Item {
                    Layout.preferredHeight: 10
                    Layout.fillWidth: true
                }

                Label {
                    text: "Enter partitions:"
                    leftPadding: 5
                    font.bold: true
                }

                RowLayout {
                    spacing: 8

                    TextField {
                        id: inputField
                        placeholderText: "Enter text"
                        Layout.fillWidth: true
                        onAccepted: addButton.clicked()
                    }

                    Button {
                        id: addButton
                        text: "Add"
                        onClicked: {
                            if (inputField.text.length > 0) {
                                partitionsModel.append({ "text": inputField.text })
                                inputField.text = ""
                                updatePartitions()
                            }
                        }
                    }
                }

                ListView {
                    id: partitionListView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: partitionsModel

                    delegate: RowLayout {
                        width: partitionListView.width
                        height: 30
                        spacing: 0

                        Label {
                            text: model.text
                            font.pixelSize: 16
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                        }

                        Button {
                            text: "Remove"
                            onClicked: {
                                partitionsModel.remove(index)
                                updatePartitions()
                            }
                        }
                    }
                }

                Button {
                    text: atcMap.isSimulationRunning() ? "Stop Airtraffic Simulation" : "Start Simulating Airtraffic"
                    Layout.fillWidth: true
                    onClicked: {
                        if (atcMap.isSimulationRunning()) {
                            atcMap.stopSimulation()
                        } else {
                            atcMap.startSimulation()
                        }
                    }
                }
            }

            AtcMap {
                id: atcMap
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
        }
    }
}
