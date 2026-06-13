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
import "qrc:/src/views"
import "qrc:/src/views/icons"


Rectangle {
    id: topicEndpointView
    color: rootWindow.isDarkMode ? Constants.darkMainContent : Constants.lightMainContent

    property int domainId
    property string topicName
    property bool hasQosMismatch: false
    property int writerCount: 0
    property int readerCount: 0

    readonly property color secondaryTextColor: rootWindow.isDarkMode
                                                ? "#c2c2c2"
                                                : "#4f4f4f"

    EndpointModel {
        id: endpointWriterModel
    }

    EndpointModel {
        id: endpointReaderModel
    }

    Connections {
        target: endpointWriterModel
        function onTopicHasQosMismatchSignal(mismatch) {
            topicEndpointView.hasQosMismatch = mismatch
        }

        function onTotalEndpointsSignal(count) {
            topicEndpointView.writerCount = count
        }
    }

    Connections {
        target: endpointReaderModel
        function onTopicHasQosMismatchSignal(mismatch) {
            topicEndpointView.hasQosMismatch = mismatch
        }

        function onTotalEndpointsSignal(count) {
            topicEndpointView.readerCount = count
        }
    }

    Component.onCompleted: {
        console.log("TopicEndpointView for topic:", topicName, ", domainId:", domainId)
        endpointWriterModel.setDomainId(parseInt(domainId), topicName, 4)
        endpointReaderModel.setDomainId(parseInt(domainId), topicName, 3)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            RowLayout {
                Layout.fillWidth: true
                spacing: 9

                DetailBadge {
                    kind: "topic"
                }

                Label {
                    text: qsTrId("Topic")
                    font.pixelSize: 20
                    font.bold: true
                }

                Item {
                    Layout.fillWidth: true
                }

                Button {
                    text: "Create Reader (Listener)"
                    onClicked: {
                        var writerTypes = endpointWriterModel.getAllTopicTypes()
                        var readerTypes = endpointReaderModel.getAllTopicTypes()
                        var combinedArray = [];

                        function addModelToCombinedArray(model) {
                            var i = 0;
                            while (i < model.length) {
                                if (combinedArray.indexOf(model[i]) === -1) {
                                    combinedArray.push(model[i]);
                                }
                                i++;
                            }
                        }
                        addModelToCombinedArray(writerTypes);
                        addModelToCombinedArray(readerTypes);
                        readerTesterDialogId.setTypes(domainId, topicName, combinedArray, 3);
                        readerTesterDialogId.open();
                    }
                }

                Button {
                    text: "Create Writer (Tester)"
                    onClicked: {
                        var writerTypes = endpointWriterModel.getAllTopicTypes()
                        var readerTypes = endpointReaderModel.getAllTopicTypes()
                        var combinedArray = [];

                        function addModelToCombinedArray(model) {
                            var i = 0;
                            while (i < model.length) {
                                if (combinedArray.indexOf(model[i]) === -1) {
                                    combinedArray.push(model[i]);
                                }
                                i++;
                            }
                        }
                        addModelToCombinedArray(writerTypes);
                        addModelToCombinedArray(readerTypes);
                        readerTesterDialogId.setTypes(domainId, topicName, combinedArray, 4);
                        readerTesterDialogId.open();
                    }
                }

                WarningTriangle {
                    id: warning_triangle
                    Layout.preferredHeight: 30
                    Layout.preferredWidth: 30
                    enableTooltip: true
                    tooltipText: "Qos mismatch detected."
                    visible: topicEndpointView.hasQosMismatch
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 14
                Layout.topMargin: 7
                Layout.bottomMargin: 14
                spacing: 8

                Label {
                    text: "Domain ID:"
                    font.pixelSize: 10
                    color: topicEndpointView.secondaryTextColor
                }

                Label {
                    text: domainId
                    font.pixelSize: 11
                    font.bold: true
                }

                Label {
                    text: "Topic Name:"
                    font.pixelSize: 10
                    color: topicEndpointView.secondaryTextColor
                    Layout.leftMargin: 12
                }

                Label {
                    Layout.fillWidth: true
                    text: topicName
                    font.pixelSize: 11
                    font.bold: true
                    elide: Text.ElideRight
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true

                        Label {
                            text: "Writers"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        Rectangle {
                            Layout.preferredWidth: writerCountLabel.implicitWidth + 12
                            Layout.preferredHeight: 20
                            radius: 10
                            color: rootWindow.isDarkMode ? "#173d63" : "#dceeff"

                            Label {
                                id: writerCountLabel
                                anchors.centerIn: parent
                                text: writerCount
                                font.pixelSize: 10
                                font.bold: true
                                color: rootWindow.isDarkMode ? "#8cc8ff" : "#145c9e"
                            }
                        }

                        Item {
                            Layout.fillWidth: true
                        }
                    }

                    ListView {
                        id: listViewWriter
                        model: endpointWriterModel
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        interactive: true
                        ScrollBar.vertical: ScrollBar {
                            policy: ScrollBar.AsNeeded
                        }

                        delegate: EndpointCard {
                            isWriter: true
                            readerModel: endpointReaderModel
                            writerModel: endpointWriterModel
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true

                        Label {
                            text: "Readers"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        Rectangle {
                            Layout.preferredWidth: readerCountLabel.implicitWidth + 12
                            Layout.preferredHeight: 20
                            radius: 10
                            color: rootWindow.isDarkMode ? "#17254f" : "#e6ebff"

                            Label {
                                id: readerCountLabel
                                anchors.centerIn: parent
                                text: readerCount
                                font.pixelSize: 10
                                font.bold: true
                                color: "#274ff6"
                            }
                        }

                        Item {
                            Layout.fillWidth: true
                        }
                    }

                    ListView {
                        id: listViewReader
                        model: endpointReaderModel
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        interactive: true

                        ScrollBar.vertical: ScrollBar {
                            policy: ScrollBar.AsNeeded
                        }

                        delegate: EndpointCard {
                            isWriter: false
                            readerModel: endpointReaderModel
                            writerModel: endpointWriterModel
                        }
                    }
                }
            }
        }
    }
}
