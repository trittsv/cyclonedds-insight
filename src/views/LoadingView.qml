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


Popup {
    property string message: qsTrId("general.loading")
    property real progress: -1
    width: parent ? parent.width : 0
    height: parent ? parent.height : 0
    x: 0
    y: 0
    modal: true
    focus: true
    closePolicy: Popup.NoAutoClose
    padding: 0
    background: Rectangle {
        color: Constants.mainContentBackgroundColor(rootWindow.isDarkMode)
    }
    contentItem: Item {
        ColumnLayout {
            anchors.centerIn: parent
            spacing: 16
            AnimatedImage {
                Layout.alignment: Qt.AlignHCenter
                source: "qrc:/res/images/spinning.gif"
                sourceSize.width: 100
                sourceSize.height: 100
                Layout.preferredWidth: 100
                Layout.preferredHeight: 100
                playing: loading.visible
            }
            Label {
                Layout.alignment: Qt.AlignHCenter
                text: loading.message
            }
            ProgressBar {
                Layout.preferredWidth: 280
                indeterminate: loading.progress < 0
                value: loading.progress < 0 ? 0 : loading.progress
            }
            Label {
                Layout.alignment: Qt.AlignHCenter
                visible: loading.progress >= 0
                text: Math.round(Math.max(0, loading.progress) * 100) + " %"
            }
        }
    }
    id: loading
}
