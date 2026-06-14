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

Item {
    id: root

    property color iconColor: "grey"
    property real lineWidth: 1.5

    implicitWidth: 18
    implicitHeight: 16

    Rectangle {
        anchors.fill: parent
        anchors.margins: root.lineWidth
        radius: 2
        color: "transparent"
        border.width: root.lineWidth
        border.color: root.iconColor

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: root.lineWidth
            color: root.iconColor
        }
    }
}
