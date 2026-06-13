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
import QtQuick.Controls
import QtQuick.Layouts

import org.eclipse.cyclonedds.insight
import "qrc:/src/views"


Rectangle {
    id: participantViewId
    color: rootWindow.isDarkMode
           ? Constants.darkMainContent
           : Constants.lightMainContent

    property int domainId
    property string participantKey
    property string vendorName
    property bool qosLoaded: false

    readonly property color surfaceColor: rootWindow.isDarkMode
                                          ? Constants.darkCardBackgroundColor
                                          : Constants.lightCardBackgroundColor
    readonly property color borderColor: rootWindow.isDarkMode
                                         ? "#464646"
                                         : "#dddddd"
    readonly property color secondaryTextColor: rootWindow.isDarkMode
                                                ? "#c2c2c2"
                                                : "#4f4f4f"

    ParticipantDetailsModel {
        id: participantModel
    }

    Component.onCompleted: {
        participantModel.start(domainId, participantKey)
    }

    Connections {
        target: participantModel

        function onUpdateQosSignal(qos) {
            qosTextArea.text = qos.startsWith("Qos:\n")
                    ? qos.substring(5)
                    : qos
            participantViewId.qosLoaded = true
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 14

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 7

            RowLayout {
                Layout.fillWidth: true
                spacing: 9

                Rectangle {
                    Layout.preferredWidth: 24
                    Layout.preferredHeight: 24
                    radius: 7
                    color: rootWindow.isDarkMode ? "#3f315d" : "#eee5ff"

                    Item {
                        anchors.centerIn: parent
                        width: 12
                        height: 14

                        readonly property color iconColor: rootWindow.isDarkMode
                                                            ? "#c6a9ff"
                                                            : "#6b3fa0"

                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: 6
                            height: 6
                            radius: 3
                            color: parent.iconColor
                        }

                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.bottom: parent.bottom
                            width: 12
                            height: 7
                            radius: 3.5
                            color: parent.iconColor
                        }
                    }
                }

                Label {
                    text: qsTrId("participant.title")
                    font.pixelSize: 20
                    font.bold: true
                }

                Item {
                    Layout.fillWidth: true
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 14
                spacing: 8

                Label {
                    text: qsTrId("participant.domain") + ":"
                    font.pixelSize: 10
                    color: participantViewId.secondaryTextColor
                }

                Label {
                    text: participantViewId.domainId
                    font.pixelSize: 11
                    font.bold: true
                }

                Label {
                    text: qsTrId("participant.vendor") + ":"
                    font.pixelSize: 10
                    color: participantViewId.secondaryTextColor
                    Layout.leftMargin: 12
                }

                Label {
                    Layout.fillWidth: true
                    text: participantViewId.vendorName.length > 0
                          ? participantViewId.vendorName
                          : qsTrId("participant.unknown")
                    font.pixelSize: 11
                    font.bold: true
                    elide: Text.ElideRight
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 14
                spacing: 8

                Label {
                    text: qsTrId("participant.key") + ":"
                    font.pixelSize: 10
                    color: participantViewId.secondaryTextColor
                }

                Text {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 17
                    text: participantViewId.participantKey
                    color: rootWindow.isDarkMode ? "#e0e0e0" : "#303030"
                    font.pixelSize: 11
                    minimumPixelSize: 8
                    fontSizeMode: Text.HorizontalFit
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 140
            radius: 8
            color: participantViewId.surfaceColor
            border.width: 1
            border.color: participantViewId.borderColor

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                Label {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 36
                    Layout.leftMargin: 12
                    text: qsTrId("participant.qos")
                    font.pixelSize: 13
                    font.bold: true
                    verticalAlignment: Text.AlignVCenter
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    color: rootWindow.isDarkMode
                           ? Constants.darkSeparator
                           : Constants.lightSeparator
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    Label {
                        anchors.centerIn: parent
                        visible: !participantViewId.qosLoaded
                        text: qsTrId("participant.loading")
                        color: participantViewId.secondaryTextColor
                        font.pixelSize: 11
                    }

                    ScrollView {
                        id: qosScrollView
                        anchors.fill: parent
                        visible: participantViewId.qosLoaded
                        clip: true
                        contentWidth: availableWidth
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        ScrollBar.vertical.policy: ScrollBar.AsNeeded

                        TextEdit {
                            id: qosTextArea
                            width: qosScrollView.availableWidth
                            text: ""
                            readOnly: true
                            selectByMouse: true
                            wrapMode: TextEdit.Wrap
                            padding: 12
                            color: rootWindow.isDarkMode
                                   ? "#e0e0e0"
                                   : "#303030"
                            font.pixelSize: 11
                        }
                    }
                }
            }
        }
    }
}
