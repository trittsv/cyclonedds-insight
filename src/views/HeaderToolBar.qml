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
import "qrc:/src/views/icons"

ToolBar {
    id: headerToolBar
    topPadding: 10 + ((Qt.platform.os === "android" || Qt.platform.os === "ios") ? SafeArea.margins.top : 0)
    bottomPadding: 10
    leftPadding: 10 + ((Qt.platform.os === "android" || Qt.platform.os === "ios") ? SafeArea.margins.left : 0)
    rightPadding: 10 + ((Qt.platform.os === "android" || Qt.platform.os === "ios") ? SafeArea.margins.right : 0)
    property bool isStartupSpinning: true
    readonly property bool mobileToolbar: (Qt.platform.os === "android" || Qt.platform.os === "ios")
    property int startupSpinLoops: 0
    property bool isActivitySpinning: false
    readonly property bool isHeaderSpinning: isStartupSpinning || isActivitySpinning

    function startLogoSpin() {
        startupSpinLoops = 0
        isStartupSpinning = true
        headerLoadingId.currentFrame = 0
    }

    background: Rectangle {
        anchors.fill: parent
        color: Constants.headerBackgroundColor(rootWindow.isDarkMode)
    }

    Connections {
        target: treeModel
        function onDiscover_domains_running_signal(active) {
            headerToolBar.isActivitySpinning = active
        }
    }

    contentItem: RowLayout {

        Item {
            Layout.preferredWidth: 30
            Layout.minimumWidth: 30
            Layout.preferredHeight: 30

            Image {
                id: cycloneLogo
                visible: headerToolBar.mobileToolbar || !isHeaderSpinning
                source: "qrc:/res/images/cyclonedds.png"
                sourceSize.width: 30
                sourceSize.height: 30
                NumberAnimation on rotation {
                    from: 0
                    to: 360
                    duration: 1000
                    running: headerToolBar.mobileToolbar && headerToolBar.isHeaderSpinning
                    loops: headerToolBar.isActivitySpinning ? Animation.Infinite : 2
                    onFinished: headerToolBar.isStartupSpinning = false
                }
            }
            AnimatedImage {
                id: headerLoadingId
                source: headerToolBar.mobileToolbar ? "" : "qrc:/res/images/spinning.gif"
                visible: !headerToolBar.mobileToolbar && isHeaderSpinning
                playing: !headerToolBar.mobileToolbar && isHeaderSpinning
                paused: !isHeaderSpinning
                sourceSize.height: 30
                sourceSize.width: 30
                height: 30
                width: 30

                onCurrentFrameChanged: {
                    if (headerToolBar.isStartupSpinning
                            && frameCount > 1
                            && currentFrame === frameCount - 1) {
                        headerToolBar.startupSpinLoops++
                        if (headerToolBar.startupSpinLoops >= 2) {
                            headerToolBar.isStartupSpinning = false
                        }
                    }
                }
            }

            MouseArea {
                anchors.fill: parent
                onClicked: headerToolBar.startLogoSpin()
            }
        }

        Label {
            text: rootWindow.title
            Layout.fillWidth: headerToolBar.mobileToolbar
            Layout.minimumWidth: 0
            elide: Text.ElideRight
        }
        Item {
            visible: !headerToolBar.mobileToolbar
            Layout.fillWidth: true
        }
        ComboBox {
            model: langModel
            textRole: "name"
            currentIndex: langModel.currentLanguageIndex
            Layout.preferredWidth: 145
            focusPolicy: Qt.NoFocus
            onActivated: function(index) {
                langModel.loadLanguageByIndex(index)
            }
        }
        ToolButton {
            id: menuButton
            onClicked: menu.open()
            flat: true

            MenuIcon {
                anchors.centerIn: parent
                width: 18
                height: 18
                z: 1
                iconColor: Constants.mutedForegroundColor(rootWindow.isDarkMode)
            }

            Menu {
                id: menu
                y: menuButton.height

                MenuItem {
                    text: qsTrId("general.home")
                    onClicked: layout.currentIndex = 1
                }
                MenuItem {
                    text: qsTrId("general.shapedemo")
                    onClicked: shapeDemoViewId.visible = true
                }
                MenuItem {
                    text: qsTrId("general.settings")
                    onClicked: layout.currentIndex = 0
                }
                MenuItem {
                    text: qsTrId("general.configeditor")
                    onTriggered: layout.currentIndex = 2
                }
                MenuItem {
                    text: qsTrId("log.show")
                    onTriggered: logViewId.visible = true
                }
                MenuItem {
                    text: qsTrId("general.export.ddsentities")
                    onTriggered: exportDdsSystemFileDialog.open()
                }
                MenuItem {
                    text: qsTrId("general.checkupdates")
                    enabled: !IS_MOBILE
                    onTriggered: checkForUpdatesWindow.showAndCheckForUpdates()
                }
                MenuItem {
                    text: qsTrId("general.about")
                    onClicked: aboutWindow.visible = true
                }
            }
        }
    }
}
