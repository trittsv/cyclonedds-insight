/*
 * Copyright(c) 2026 Sven Trittler
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
import QtQuick.Controls
import QtQuick.Layouts

import org.eclipse.cyclonedds.insight
import "qrc:/src/views"

Item {
    id: card
    objectName: "endpointCard"

    required property bool isWriter
    required property var readerModel
    required property var writerModel
    required property string endpoint_key
    required property string endpoint_participant_key
    required property string endpoint_participant_instance_handle
    required property string endpoint_topic_name
    required property string endpoint_topic_type
    required property string endpoint_qos
    required property string endpoint_type_id
    required property string endpoint_hostname
    required property string endpoint_process_id
    required property string endpoint_process_name
    required property string addresses
    required property bool endpoint_has_qos_mismatch
    required property string endpoint_qos_mismatch_text
    required property var partitions
    required property bool has_partitions

    width: ListView.view ? ListView.view.width : 0
    height: 104

    readonly property color accentColor: card.isWriter
        ? rootWindow.isDarkMode ? "#8cc8ff" : "#145c9e"
        : "#274ff6"

    readonly property string endpointDetails:
        "Key: " + endpoint_key
        + "\nParticipant Key: " + endpoint_participant_key
        + "\nInstance Handle: " + endpoint_participant_instance_handle
        + "\nTopic Name: " + endpoint_topic_name
        + "\nTopic Type: " + endpoint_topic_type
        + endpoint_qos_mismatch_text
        + "\nQos:\n" + endpoint_qos
        + "\nType Id: " + endpoint_type_id

    Rectangle {
        id: surface
        anchors.fill: parent
        anchors.leftMargin: 1
        anchors.rightMargin: 6
        anchors.bottomMargin: 8
        radius: 8
        color: {
            return rootWindow.isDarkMode
                    ? Constants.darkCardBackgroundColor
                    : Constants.lightCardBackgroundColor
        }
        border.width: 1
        border.color: card.endpoint_has_qos_mismatch
                      ? Constants.warningColor
                      : rootWindow.isDarkMode ? "#464646" : "#dddddd"

        Rectangle {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.topMargin: 7
            anchors.bottomMargin: 7
            width: 3
            radius: 2
            color: card.accentColor
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 10
            anchors.topMargin: 6
            anchors.bottomMargin: 5
            spacing: 2

            RowLayout {
                Layout.fillWidth: true
                spacing: 7

                Rectangle {
                    Layout.preferredWidth: 8
                    Layout.preferredHeight: 8
                    radius: 4
                    color: Constants.warningColor
                    visible: card.endpoint_has_qos_mismatch
                }

                Label {
                    Layout.fillWidth: true
                    text: card.endpoint_process_name.length > 0
                          ? card.endpoint_process_name
                          : "Unknown process"
                    font.pixelSize: 13
                    font.bold: true
                    elide: Text.ElideRight
                }

                Label {
                    text: card.endpoint_process_id.length > 0
                          ? "PID " + card.endpoint_process_id
                          : ""
                    visible: text.length > 0
                    font.pixelSize: 10
                    opacity: 0.6
                }
            }

            Label {
                id: hostAddressLabel
                Layout.fillWidth: true
                text: card.endpoint_hostname
                      + (card.addresses.length > 0
                         ? "  |  " + card.addresses
                         : "")
                font.pixelSize: 10
                color: rootWindow.isDarkMode ? "#d0d0d0" : "#454545"
                elide: Text.ElideRight

                HoverHandler {
                    id: hostAddressHover
                }

                ToolTip {
                    parent: hostAddressLabel
                    visible: hostAddressHover.hovered
                             && hostAddressLabel.truncated
                    delay: 500
                    text: hostAddressLabel.text
                }
            }

            Text {
                Layout.fillWidth: true
                Layout.preferredHeight: 12
                text: card.endpoint_key
                color: rootWindow.isDarkMode ? "#a8a8a8" : "#666666"
                font.pixelSize: 9
                minimumPixelSize: 7
                fontSizeMode: Text.HorizontalFit
                opacity: 0.62
                verticalAlignment: Text.AlignVCenter
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.rightMargin: endpointActions.width + 6
                spacing: 6

                Label {
                    text: "No partition"
                    visible: !card.has_partitions
                    font.pixelSize: 10
                    opacity: 0.55
                }

                Flickable {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 18
                    contentWidth: partitionRow.width
                    contentHeight: height
                    boundsBehavior: Flickable.StopAtBounds
                    clip: true
                    visible: card.has_partitions

                    Row {
                        id: partitionRow
                        spacing: 5

                        Repeater {
                            model: card.partitions

                            Rectangle {
                                height: 18
                                width: partitionLabel.implicitWidth + 12
                                radius: 4
                                color: partition_matched
                                       ? "#258a4b"
                                       : rootWindow.isDarkMode ? "#292929" : "#eeeeee"
                                border.width: partition_selected ? 2 : 1
                                border.color: partition_selected
                                              ? Constants.warningColor
                                              : partition_matched ? "#35b86b"
                                                                  : rootWindow.isDarkMode ? "#555555" : "#d0d0d0"

                                Label {
                                    id: partitionLabel
                                    anchors.centerIn: parent
                                    text: partition_name
                                    font.pixelSize: 10
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (partition_selected) {
                                            card.readerModel.clearPartitionMatching()
                                            card.writerModel.clearPartitionMatching()
                                        } else if (card.isWriter) {
                                            card.readerModel.setSelectedPartition(partition_name, "")
                                            card.writerModel.setSelectedPartition(
                                                partition_name, card.endpoint_key)
                                        } else {
                                            card.readerModel.setSelectedPartition(
                                                partition_name, card.endpoint_key)
                                            card.writerModel.setSelectedPartition(partition_name, "")
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

            }
        }

        Row {
            id: endpointActions
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.rightMargin: 10
            anchors.bottomMargin: 5
            spacing: 4
            height: 18

            Rectangle {
                id: previewButton
                width: previewLabel.implicitWidth + 12
                height: parent.height
                radius: 4
                color: previewMouseArea.containsMouse
                       ? rootWindow.isDarkMode ? "#444444" : "#d9d9d9"
                       : rootWindow.isDarkMode ? "#292929" : "#eeeeee"
                border.width: 1
                border.color: rootWindow.isDarkMode ? "#666666" : "#b5b5b5"

                Label {
                    id: previewLabel
                    anchors.centerIn: parent
                    text: qsTrId("endpoint.preview")
                    font.pixelSize: 9
                    color: rootWindow.isDarkMode ? "#d0d0d0" : "#505050"
                }

                MouseArea {
                    id: previewMouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                }

                ToolTip {
                    id: endpointPreview
                    parent: previewButton
                    visible: previewMouseArea.containsMouse
                    delay: 400
                    text: card.endpointDetails
                    contentItem: Label {
                        text: endpointPreview.text
                    }
                    background: Rectangle {
                        border.color: rootWindow.isDarkMode
                                      ? Constants.darkBorderColor
                                      : Constants.lightBorderColor
                        border.width: 1
                        color: rootWindow.isDarkMode
                               ? Constants.darkCardBackgroundColor
                               : Constants.lightCardBackgroundColor
                        radius: 6
                    }
                }
            }

            Rectangle {
                id: detailsButton
                width: detailsLabel.implicitWidth + 12
                height: parent.height
                radius: 4
                color: detailsMouseArea.pressed
                       ? rootWindow.isDarkMode ? "#444444" : "#d9d9d9"
                       : rootWindow.isDarkMode ? "#292929" : "#eeeeee"
                border.width: 1
                border.color: card.accentColor

                Label {
                    id: detailsLabel
                    anchors.centerIn: parent
                    text: qsTrId("endpoint.details")
                    font.pixelSize: 9
                    font.bold: true
                    color: card.accentColor
                }

                MouseArea {
                    id: detailsMouseArea
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: (mouse) => {
                        if (detailWindow.visible) {
                            detailWindow.raise()
                            return
                        }
                        const globalPosition = mapToGlobal(mouse.x, mouse.y)
                        detailWindow.x =
                                globalPosition.x - detailWindow.width / 2
                        detailWindow.y = globalPosition.y
                        detailWindow.visible = true
                    }
                }
            }
        }
    }

    EndpointDetailWindow {
        id: detailWindow
        title: (card.isWriter ? "Writer " : "Reader ") + card.endpoint_key
        endpointText: card.endpointDetails
    }
}
