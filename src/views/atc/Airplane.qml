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



Item {
    id: root
    property real heading: 0
    property string planeId: "avx123"
    property color planeColor: "yellow"
    property real scale: 1.0
    property real lat: 0.7
    property real lon: 0.7
    property int lastUpdate: 0

    width: 40 * scale
    height: 40 * scale

    function redraw() {
        planeCanvas.requestPaint();
    }

    Canvas {
        id: planeCanvas
        anchors.fill: parent
        onPaint: {
            var ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);
            ctx.save();

            var cx = width / 2;
            var cy = height / 2;
            ctx.translate(cx, cy);
            //ctx.rotate(root.heading * Math.PI / 180);
            ctx.rotate((heading + 180) * Math.PI / 180);
            var s = Math.min(width, height) / 40;
            ctx.scale(s, s);

            // Fuselage
            ctx.beginPath();
            ctx.moveTo(0, -12);
            ctx.lineTo(2, -2);
            ctx.lineTo(1, 12);
            ctx.lineTo(-1, 12);
            ctx.lineTo(-2, -2);
            ctx.closePath();
            ctx.fillStyle = planeColor;
            ctx.fill();
            ctx.lineWidth = 1;       // border thickness
            ctx.strokeStyle = "black"; // border color
            ctx.stroke();

            // Realistic Wings
            ctx.beginPath();
            ctx.moveTo(-8, 0);
            ctx.lineTo(-12, 3);
            ctx.lineTo(-10, 4);
            ctx.lineTo(10, 4);
            ctx.lineTo(12, 3);
            ctx.lineTo(8, 0);
            ctx.closePath();
            ctx.fill();
            ctx.stroke();

            // Tail
            ctx.beginPath();
            ctx.moveTo(-3, -12);
            ctx.lineTo(3, -12);
            ctx.lineTo(0, -8);
            ctx.closePath();
            ctx.fill();
            ctx.stroke();

            ctx.restore();
        }
    }

    Label {
        id: label
        text: planeId
        visible: false
        anchors.top: planeCanvas.bottom
        anchors.horizontalCenter: planeCanvas.horizontalCenter
        color: "black"
        font.pointSize: 15 * scale
        font.bold: true

        Rectangle {
            anchors.fill: parent
            color: "white"
            z: -1
        }
    }
}
