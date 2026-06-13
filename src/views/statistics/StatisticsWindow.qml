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
import "qrc:/src/views/icons"
import "qrc:/src/views/selection_details"


Rectangle {
    id: statisticsMainViewId
    anchors.fill: parent
    color: rootWindow.isDarkMode ? Constants.darkMainContent : Constants.lightMainContent
    property bool statsRunning: false
    readonly property color secondaryTextColor: rootWindow.isDarkMode
                                                ? "#c2c2c2"
                                                : "#4f4f4f"

    ColumnLayout {
        anchors.fill: parent
        spacing: 14
        anchors.margins: 16

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 7

            RowLayout {
                Layout.fillWidth: true
                spacing: 9

                DetailBadge {
                    kind: "statistics"
                }

                Label {
                    text: qsTrId("statistics")
                    font.pixelSize: 20
                    font.bold: true
                }

                Item {
                    Layout.fillWidth: true
                }

                Rectangle {
                    Layout.preferredWidth: 8
                    Layout.preferredHeight: 8
                    radius: 4
                    color: statisticsMainViewId.statsRunning
                           ? "#36a269"
                           : "#d04a4a"
                }

                Label {
                    text: statisticsMainViewId.statsRunning
                          ? qsTrId("statistic.status.running")
                          : qsTrId("statistic.status.stopped")
                    font.pixelSize: 11
                    font.bold: true
                }
            }

            Label {
                Layout.fillWidth: true
                Layout.leftMargin: 14
                text: qsTrId("statistic.monitor.usage.hint")
                font.pixelSize: 10
                color: statisticsMainViewId.secondaryTextColor
                elide: Text.ElideRight
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 0

            GroupBox {
                id: settingsGroubBox
                title: qsTrId("general.settings")
                spacing: 0

                ColumnLayout {
                    Layout.fillHeight: true
                    Layout.fillWidth: true
                    spacing: 0

                    RowLayout {
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        spacing: 0

                        Label {
                            text: "Update Interval:"
                        }

                        ComboBox {
                            id: updateRateSelector
                            Layout.preferredWidth: 70
                            model: ["1", "2", "3", "5", "8", "10", "30", "60", "900", "1800", "3600"]
                            currentIndex: 2
                            onCurrentTextChanged: statisticModelId.setUpdateInterval(parseInt(currentText))
                        }

                        Label {
                            text: "seconds."
                        }
                    }

                    RowLayout {
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        spacing: 0

                        Label {
                            text: "Show data from last"
                        }

                        ComboBox {
                            Layout.preferredWidth: 70
                            model: ["1", "2", "3", "5", "8", "13", "21", "34", "55", "89", "144", "233", "720" ,"1440"]
                            currentIndex: 1
                            onCurrentTextChanged: statisticsView.setKeepHistoryMinutes(parseInt(currentText))
                        }

                        Label {
                            text: "minutes."
                        }
                    }


                    RowLayout {
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        spacing: 0

                        Label {
                            text: "Aggregate by:"
                        }

                        ComboBox {
                            id: aggregateByComboBoxId
                            Layout.preferredWidth: 150
                            model: ["Domain", "Host", "Process", "Participant", "Topic", "Writer"]
                            currentIndex: 2
                            onCurrentTextChanged: {
                                statisticsView.clearStatistics()
                                statisticModelId.setAggregation(currentText)
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        spacing: 0
                        Button {
                            text: statsRunning ? qsTrId("statistics.stop") : qsTrId("statistics.start")
                            onClicked: {
                                if (statsRunning) {
                                    statisticsView.stopStatistics()
                                } else {
                                    statisticsView.startStatistics()
                                }
                                statsRunning = !statsRunning
                            }
                        }
                    }
                }
            }

            GroupBox {
                id: chatGroubBox
                title: qsTrId("statistic.chart.controls")
                spacing: 0
                Layout.preferredHeight: settingsGroubBox.height

                ColumnLayout {
                    Layout.fillHeight: true
                    Layout.fillWidth: true
                    spacing: 0

                    RowLayout {
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        spacing: 0

                        Button {
                            ArrowIcon {
                                anchors.centerIn: parent
                                z: 1
                                direction: "left"
                                iconColor: rootWindow.isDarkMode ? "#d0d0d0" : "#505050"
                            }
                            onClicked: {
                                if (statisticsView.itemChartWidth >= 400) {
                                    statisticsView.itemChartWidth -= 50
                                }
                            }
                        }
                        Button {
                            ArrowIcon {
                                anchors.centerIn: parent
                                z: 1
                                direction: "right"
                                iconColor: rootWindow.isDarkMode ? "#d0d0d0" : "#505050"
                            }
                            onClicked: {
                                statisticsView.itemChartWidth += 50
                            }
                        }
                        Button {
                            ArrowIcon {
                                anchors.centerIn: parent
                                z: 1
                                direction: "up"
                                iconColor: rootWindow.isDarkMode ? "#d0d0d0" : "#505050"
                            }
                            onClicked: {
                                if (statisticsView.itemCellHeight >= 300) {
                                    statisticsView.itemCellHeight -= 50
                                }
                            }
                        }
                        Button {
                            ArrowIcon {
                                anchors.centerIn: parent
                                z: 1
                                direction: "down"
                                iconColor: rootWindow.isDarkMode ? "#d0d0d0" : "#505050"
                            }
                            onClicked: {
                                statisticsView.itemCellHeight += 50
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 30
                        spacing: 0

                        Button {
                            text: "Add Marker"
                            enabled: statsRunning
                            onClicked: {
                                statisticsView.addMarkerToAllCharts(markerTextField.text, Date.now()); 
                            }
                        }
                        Button {
                            text: "Clear Markers"
                            onClicked: clearMarkerDialog.open()
                        }
                    }
                    TextField {
                        id: markerTextField
                        placeholderText: "Enter Marker Name"
                        Layout.fillWidth: true
                    }
                }
            }

            Rectangle {
                id: statErrorWindow
                color: "transparent"
                Layout.fillWidth: true   
                Layout.preferredHeight: settingsGroubBox.height
                visible: false

                Flickable {
                    id: statisticErrorsScrollView
                    anchors.fill: parent
                    boundsBehavior: Flickable.StopAtBounds
                    interactive: true
                    ScrollBar.vertical: ScrollBar {}

                    TextArea.flickable: TextArea {
                        id: statErrorTextArea
                        readOnly: true
                        tabStopDistance: 40
                        wrapMode: TextArea.Wrap
                        selectByMouse: true
                        selectByKeyboard: true
                        onContentHeightChanged: {
                            statErrorTextArea.cursorPosition = statErrorTextArea.length
                            statisticErrorsScrollView.contentY = statErrorTextArea.height - statisticErrorsScrollView.height
                        }
                    }
                }
                Button {
                    text: qsTrId("general.clear")
                    anchors.top: statErrorWindow.top
                    anchors.right: statErrorWindow.right
                    anchors.margins: 10
                    onClicked: {
                        statErrorWindow.visible = false
                        statErrorTextArea.text = ""
                    }
                }
            }
        }

        StatisticsModel {
            id: statisticModelId
            Component.onDestruction: {
                statisticModelId.stop()
            }
        }

        Connections {
            target: statisticModelId
            function onStatisticError(msg) {
                if (!statErrorWindow.visible) {
                    statErrorWindow.visible = true
                }

                statErrorTextArea.append(msg)
            }
        }

        StatisticsView {
            id: statisticsView
            statisticModel: statisticModelId
            visible: true
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }

    MessageDialog {
        id: clearMarkerDialog
        title: qsTrId("general.alert");
        text: qsTrId("statistic.clear.markers.confirm");
        buttons: MessageDialog.Ok | MessageDialog.Cancel;
        onButtonClicked: function (button, role) {
            if (role === MessageDialog.AcceptRole || role === MessageDialog.YesRole) {
                statisticsView.clearMarkers()
            }
        }
    }

    function aboutToClose() {
        console.log("StatisticsWindow is closing")
        statisticsView.stopStatistics()
        statsRunning = false
    }
}
