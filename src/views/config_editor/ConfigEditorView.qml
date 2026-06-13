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

import QtCore
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

import org.eclipse.cyclonedds.insight
import "qrc:/src/views"
import "qrc:/src/views/icons"
import "qrc:/src/views/selection_details"

Rectangle {
    id: configEditorView

    color: rootWindow.isDarkMode
           ? Constants.darkMainContent
           : Constants.lightMainContent

    property string fileContent: ""
    property string lastSavedTime: ""
    property bool configFileAvailable: false
    property int currentTab: 0

    readonly property color surfaceColor: rootWindow.isDarkMode
                                          ? Constants.darkCardBackgroundColor
                                          : Constants.lightCardBackgroundColor
    readonly property color borderColor: rootWindow.isDarkMode
                                         ? "#464646"
                                         : "#dddddd"
    readonly property color secondaryTextColor: rootWindow.isDarkMode
                                                ? "#c2c2c2"
                                                : "#4f4f4f"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.bottomMargin: 14
            spacing: 9

            DetailBadge {
                kind: "configuration"
            }

            Label {
                text: qsTrId("general.configeditor")
                font.pixelSize: 20
                font.bold: true
            }

            Item {
                Layout.fillWidth: true
            }
        }

        Row {
            id: tabRow
            Layout.preferredHeight: 30
            Layout.bottomMargin: -1
            spacing: 3
            z: 2

            Repeater {
                model: [
                    qsTrId("config.tab.file"),
                    qsTrId("config.tab.configdocumentation")
                ]

                Rectangle {
                    id: tab

                    required property int index
                    required property string modelData
                    readonly property bool selected: index === configEditorView.currentTab

                    width: Math.max(150, tabLabel.implicitWidth + 32)
                    height: selected ? 30 : 27
                    y: selected ? 0 : 3
                    radius: 6
                    color: selected
                           ? configEditorView.surfaceColor
                           : rootWindow.isDarkMode
                             ? "#383838"
                             : "#e2e2e2"
                    border.width: 1
                    border.color: selected
                                  ? configEditorView.borderColor
                                  : rootWindow.isDarkMode
                                    ? Constants.darkSeparator
                                    : Constants.lightSeparator
                    opacity: selected || tabMouseArea.containsMouse ? 1 : 0.78

                    Rectangle {
                        visible: tab.selected
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.leftMargin: 1
                        anchors.rightMargin: 1
                        height: 2
                        color: parent.color
                    }

                    Label {
                        id: tabLabel
                        anchors.centerIn: parent
                        text: tab.modelData
                        font.pixelSize: 13
                        font.bold: tab.selected
                    }

                    MouseArea {
                        id: tabMouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: configEditorView.currentTab = tab.index
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 8
            color: configEditorView.surfaceColor
            border.width: 1
            border.color: configEditorView.borderColor
            clip: true
            z: 1

            StackLayout {
                anchors.fill: parent
                currentIndex: configEditorView.currentTab

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 3

                                Label {
                                    text: "CYCLONEDDS_URI"
                                    font.pixelSize: 10
                                    color: configEditorView.secondaryTextColor
                                }

                                TextField {
                                    id: uriField
                                    Layout.fillWidth: true
                                    text: CYCLONEDDS_URI
                                    readOnly: true
                                    selectByMouse: true
                                }
                            }

                            Button {
                                visible: configEditorView.configFileAvailable
                                text: "Reload"
                                flat: true
                                onClicked: {
                                    configEditorView.fileContent =
                                            qmlUtils.loadFileContent(CYCLONEDDS_URI)
                                    configTextArea.text =
                                        configEditorView.fileContent
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 6
                            color: rootWindow.isDarkMode ? "#191919" : "#ffffff"
                            border.width: 1
                            border.color: configEditorView.borderColor
                            clip: true

                            ScrollView {
                                anchors.fill: parent
                                visible: configEditorView.configFileAvailable
                                contentWidth: availableWidth
                                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                                ScrollBar.vertical.policy: ScrollBar.AsNeeded

                                TextArea {
                                    id: configTextArea
                                    width: parent.width
                                    text: configEditorView.fileContent
                                    wrapMode: TextEdit.Wrap
                                    selectByMouse: true
                                    selectByKeyboard: true
                                    background: null
                                    padding: 10

                                    onTextChanged: {
                                        qmlUtils.saveFileContent(
                                            CYCLONEDDS_URI, text)
                                        configEditorView.lastSavedTime =
                                            new Date().toLocaleString()
                                    }
                                }
                            }

                            Column {
                                anchors.centerIn: parent
                                width: Math.min(parent.width - 40, 440)
                                spacing: 12
                                visible: !configEditorView.configFileAvailable

                                Label {
                                    width: parent.width
                                    horizontalAlignment: Text.AlignHCenter
                                    text: "No configuration file was found in CYCLONEDDS_URI."
                                    font.pixelSize: 13
                                    font.bold: true
                                    wrapMode: Text.Wrap
                                }

                                Label {
                                    width: parent.width
                                    horizontalAlignment: Text.AlignHCenter
                                    text: "Create a new XML file and configure the environment variable to use it."
                                    font.pixelSize: 10
                                    color: configEditorView.secondaryTextColor
                                    wrapMode: Text.Wrap
                                }

                                Button {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: "Create New Configuration"
                                    highlighted: true
                                    onClicked: fileDialog.open()
                                }

                                TextEdit {
                                    id: envHintText
                                    width: parent.width
                                    visible: text.length > 0
                                    readOnly: true
                                    wrapMode: Text.WordWrap
                                    selectByMouse: true
                                    horizontalAlignment: Text.AlignHCenter
                                    color: rootWindow.isDarkMode
                                           ? "#e0e0e0"
                                           : "#303030"
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            visible: configEditorView.configFileAvailable

                            Label {
                                text: "Changes take effect after restarting the application."
                                font.pixelSize: 10
                                color: configEditorView.secondaryTextColor
                            }

                            Item {
                                Layout.fillWidth: true
                            }

                            Label {
                                text: configEditorView.lastSavedTime.length > 0
                                      ? "Automatically saved: "
                                        + configEditorView.lastSavedTime
                                      : "Automatically saved"
                                font.pixelSize: 10
                                color: configEditorView.secondaryTextColor
                            }
                        }
                    }

                    FileDialog {
                        id: fileDialog
                        currentFolder: StandardPaths.standardLocations(
                                           StandardPaths.HomeLocation)[0]
                        fileMode: FileDialog.SaveFile
                        defaultSuffix: "xml"
                        title: "Create New Configuration File"

                        onAccepted: {
                            qmlUtils.createFileFromQUrl(selectedFile)
                            const localPath =
                                qmlUtils.toLocalFile(selectedFile)
                            envHintText.text =
                                "The new configuration file has been created.\n\n"
                                + "Set the environment variable:\n"
                                + "CYCLONEDDS_URI=file://" + localPath
                                + "\n\nThen restart the application."
                            const defaultConfig =
`<?xml version="1.0" encoding="UTF-8" ?>
<CycloneDDS xmlns="https://cdds.io/config" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="https://cdds.io/config https://raw.githubusercontent.com/eclipse-cyclonedds/cyclonedds/master/etc/cyclonedds.xsd">
    <Domain Id="any">
        <General>
            <Interfaces>
                <NetworkInterface autodetermine="true" priority="default" multicast="default" />
            </Interfaces>
        </General>
    </Domain>
</CycloneDDS>
`
                            qmlUtils.saveFileContent(localPath, defaultConfig)
                        }
                    }

                    Component.onCompleted: {
                        if (qmlUtils.isValidFile(CYCLONEDDS_URI)
                                && CYCLONEDDS_URI !== "<not set>"
                                && CYCLONEDDS_URI !== "") {
                            configEditorView.configFileAvailable = true
                            configEditorView.fileContent =
                                qmlUtils.loadFileContent(CYCLONEDDS_URI)
                            configTextArea.text =
                                configEditorView.fileContent
                        } else {
                            configEditorView.configFileAvailable = false
                        }
                    }
                }

                Item {
                    SplitView {
                        id: configBrowserSplit
                        anchors.fill: parent
                        anchors.margins: 10

                        Rectangle {
                            SplitView.preferredWidth: 300
                            SplitView.minimumWidth: 180
                            color: "transparent"

                            TreeView {
                                id: treeView
                                anchors.fill: parent
                                clip: true
                                ScrollBar.vertical: ScrollBar {}
                                selectionModel: ItemSelectionModel {
                                    onCurrentIndexChanged: {
                                        details.text =
                                            modelXsd.detailsAt(currentIndex)
                                    }
                                }
                                model: modelXsd

                                delegate: Item {
                                    implicitWidth: treeView.width
                                    implicitHeight: label.implicitHeight * 1.6

                                    readonly property real indentation: 20
                                    readonly property real padding: 5

                                    required property TreeView treeView
                                    required property bool isTreeNode
                                    required property bool expanded
                                    required property int hasChildren
                                    required property int depth
                                    required property int row
                                    required property int column
                                    required property bool current

                                    Rectangle {
                                        anchors.fill: parent
                                        visible: row === treeView.currentRow
                                        color: rootWindow.isDarkMode
                                               ? Constants.darkSelectionBackground
                                               : Constants.lightSelectionBackground
                                        opacity: 0.3
                                        radius: 5
                                    }

                                    ChevronIcon {
                                        width: 14
                                        height: 14
                                        x: padding + depth * indentation
                                        anchors.verticalCenter: parent.verticalCenter
                                        visible: isTreeNode && hasChildren
                                        iconColor: rootWindow.isDarkMode
                                                   ? "#d0d0d0"
                                                   : "#505050"
                                        direction: expanded ? "down" : "right"

                                        TapHandler {
                                            onSingleTapped: {
                                                const itemIndex =
                                                    treeView.index(row, column)
                                                treeView.selectionModel
                                                    .setCurrentIndex(
                                                        itemIndex,
                                                        ItemSelectionModel.NoUpdate)
                                                treeView.toggleExpanded(row)
                                            }
                                        }
                                    }

                                    Label {
                                        id: label
                                        x: padding + (isTreeNode
                                                      ? (depth + 1)
                                                        * indentation
                                                      : 0)
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: parent.width - padding - x - 10
                                        clip: true
                                        text: model.display
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }

                        Rectangle {
                            SplitView.fillWidth: true
                            color: rootWindow.isDarkMode ? "#191919" : "#ffffff"
                            border.width: 1
                            border.color: configEditorView.borderColor
                            radius: 6
                            clip: true

                            ScrollView {
                                anchors.fill: parent
                                contentWidth: availableWidth
                                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                                TextArea {
                                    id: details
                                    width: parent.width
                                    readOnly: true
                                    wrapMode: TextEdit.Wrap
                                    text: qsTrId("general.nothing.selected")
                                    padding: 16
                                    background: null
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
