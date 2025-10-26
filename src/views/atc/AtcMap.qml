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
    id: mapView

    // Map center and zoom level
    property real centerLat: 49.36990613323239
    property real centerLon: 12.360831912406784
    property int zoom: 4
    property var airplanes: ({})
    property var routes: ({})
    property bool paused: false

    MapData {
        id: mapData
    }

    // ==== Conversion Functions (Web Mercator) ====
    function latLonToPixel(lat, lon, zoom) {
        const tileSize = 256;
        const scale = (1 << zoom) * tileSize;
        const x = (lon + 180) / 360 * scale;
        const sinLat = Math.sin(lat * Math.PI / 180);
        const y = (0.5 - Math.log((1 + sinLat) / (1 - sinLat)) / (4 * Math.PI)) * scale;
        return { x: x, y: y };
    }

    function latLonToRelativePixel(lat, lon, centerLat, centerLon, zoom, width, height) {
        const center = latLonToPixel(centerLat, centerLon, zoom);
        const point = latLonToPixel(lat, lon, zoom);
        const dx = point.x - center.x;
        const dy = point.y - center.y;
        return {
            x: width / 2 + dx,
            y: height / 2 + dy
        };
    }

    function isPointInPolygon(lat, lon, polygon) {
        // polygon = array of {lat: xx, lon: xx}
        var inside = false;
        for (var i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
            var xi = polygon[i].lat, yi = polygon[i].lon;
            var xj = polygon[j].lat, yj = polygon[j].lon;

            var intersect = ((yi > lon) != (yj > lon)) &&
                            (lat < (xj - xi) * (lon - yi) / (yj - yi) + xi);
            if (intersect) inside = !inside;
        }
        return inside;
    }

    function addAirplane(id, lat, lon) {
        var airplaneComponent = Qt.createComponent("qrc:/src/views/atc/Airplane.qml");
        if (airplaneComponent.status !== Component.Ready) {
            console.error("Failed to load Airplane.qml:", airplaneComponent.errorString());
            return;
        }

        var planeObj = airplaneComponent.createObject(mapView, { planeId: id, lat: lat, lon: lon, lastUpdate: Date.now(), visible: false });
        airplanes[id] = planeObj
        updateAirplane(id, lat, lon);
    }

    function calculateHeading(lat1, lon1, lat2, lon2) {
        // Convert degrees to radians
        var φ1 = lat1 * Math.PI / 180;
        var φ2 = lat2 * Math.PI / 180;
        var Δλ = (lon2 - lon1) * Math.PI / 180;

        // Calculate bearing
        var y = Math.sin(Δλ) * Math.cos(φ2);
        var x = Math.cos(φ1) * Math.sin(φ2) -
                Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ);
        var θ = Math.atan2(y, x);

        // Convert radians to degrees
        var bearing = θ * 180 / Math.PI;

        // Normalize to 0–360 degrees
        bearing = (bearing + 360) % 360;

        return bearing;
    }

    function getCurrentRegion(lat, lon) {
        for (var i = 0; i < mapData.countries.length; i++) {
            var country = mapData.countries[i];
            if (isPointInPolygon(lat, lon, country.boundary)) {
                return country.regionPartition;
            }
        }
        return "/Unknown";
    }

    function startSimulation() {
        demoTimer.start();
    }

    function stopSimulation() {
        demoTimer.stop();
    }

    function clearAirplanes() {
        for (var id in airplanes) {
            if (airplanes.hasOwnProperty(id)) {
                airplanes[id].destroy();
            }
        }
        airplanes = ({});
        canvas.requestPaint();
    }

    function updateAirplane(id, lat, lon) {
        if (airplanes[id] !== undefined) {
            var plane = airplanes[id];

            // Previous position
            var oldLat = plane.lat;
            var oldLon = plane.lon;

            // Update lat/lon
            plane.lat = lat;
            plane.lon = lon;

            // Convert to screen coordinates
            var pos = latLonToRelativePixel(
                plane.lat, plane.lon,
                centerLat, centerLon, zoom,
                width, height
            );
            plane.x = pos.x - (plane.width / 2);
            plane.y = pos.y - (plane.height / 2);
            plane.lastUpdate = Date.now();
            plane.visible = true;

            // Heading
            var heading =  calculateHeading(oldLat, oldLon, lat, lon);
            plane.heading = heading
            plane.redraw()
        }
    }

    function removeAirplane(id) {
        if (airplanes[id] !== undefined) {
            console.debug("Removing airplane:", id);
            airplanes[id].destroy();
            delete airplanes[id];
            canvas.requestPaint();
        }
    }

    function centroid(points) {
        var latSum = 0;
        var lonSum = 0;
        for (var i = 0; i < points.length; i++) {
            latSum += points[i].lat;
            lonSum += points[i].lon;
        }
        return { lat: latSum / points.length, lon: lonSum / points.length };
    }

    Canvas {
        id: canvas
        anchors.fill: parent
        onPaint: {
            var ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);

            // Draw each country
            for (var i = mapData.countries.length - 1; i >= 0; i--) {
                var c = mapData.countries[i];
                var pts = c.boundary;
                if (pts.length < 3)
                    continue;

                // Draw polygon
                ctx.beginPath();
                var first = true;
                for (var j = 0; j < pts.length; j++) {
                    var p = latLonToRelativePixel(
                        pts[j].lat, pts[j].lon,
                        centerLat, centerLon, zoom, width, height
                    );
                    if (first) {
                        ctx.moveTo(p.x, p.y);
                        first = false;
                    } else {
                        ctx.lineTo(p.x, p.y);
                    }
                }
                ctx.closePath();
                ctx.fillStyle = c.color;
                ctx.strokeStyle = "#333";
                ctx.lineWidth = 1.5;
                ctx.fill();
                ctx.stroke();
            }

            // Label (country name) on top of countries
            for (var i = 0; i < mapData.countries.length; i++) {
                var c = mapData.countries[i];
                var pts = c.boundary;
                var center = centroid(pts);
                var pos = latLonToRelativePixel(
                    center.lat, center.lon,
                    centerLat, centerLon, zoom, width, height
                );

                ctx.font = "bold 9px sans-serif";
                ctx.textAlign = "center";

                // Measure text size
                var text = c.name;
                var textMetrics = ctx.measureText(text);
                var textWidth = textMetrics.width;
                var textHeight = 10; // approximate height for 9px font

                // Draw white background rectangle with small padding
                var padding = 1;
                ctx.fillStyle = "rgba(255, 255, 255, 0.8)"; // semi-transparent white
                ctx.fillRect(
                    pos.x - textWidth / 2 - padding,
                    pos.y - textHeight + 2 - padding,
                    textWidth + 2 * padding,
                    textHeight + 2 * padding
                );

                // Draw black text on top
                ctx.fillStyle = "#000";
                ctx.fillText(text, pos.x, pos.y);
            }
        }
    }

    function randomPlaneCode() {
        var letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
        var code = "";
        
        // Generate 2 random letters
        for (var i = 0; i < 2; i++) {
            code += letters.charAt(Math.floor(Math.random() * letters.length));
        }

        // Generate 2 or 3 random digits
        var digitsCount = Math.random() < 0.5 ? 2 : 3;
        for (var j = 0; j < digitsCount; j++) {
            code += Math.floor(Math.random() * 10); // 0-9
        }

        return code;
    }

    Connections {
        target: atcModel
        function onAirplaneUpdated (id, lat, lon, region, isRemoved) {
            console.log("ATC Model Airplane Updated:", id, lat, lon, region);
            if (airplanes[id] === undefined && !isRemoved) {
                addAirplane(id, lat, lon);
            } else {
                if (isRemoved) {
                    removeAirplane(id);
                } else {
                    updateAirplane(id, lat, lon);
                } 
            }
        }
    }

    function isSimulationRunning() {
        return demoTimer.running;
    }

    Timer {
        id: healthCheckTimer
        interval: 100
        running: true
        repeat: true

        onTriggered: {
            var now = Date.now();
            for (var id in airplanes) {
                if (!airplanes.hasOwnProperty(id)) continue;
                var plane = airplanes[id];

                var diff = now - plane.lastUpdate  * 1000;
                if (diff > 10000) {
                    //console.debug("Health check removing airplane due to timeout:", id, diff, now, plane.lastUpdate);
                    //removeAirplane(id);
                }
            }
        }
    }

    Timer {
        id: demoTimer
        interval: 100
        running: false
        repeat: true

        onRunningChanged: {
            if (running) {
                console.log("Timer started")
            } else {
                console.log("Timer stopped")
                atcModel.clearAddedAirplaines()
            }
        }

        onTriggered: {
            if (mapView.paused)
                return;

            // Occasionally spawn a new airplane
            if (Math.random() < 0.5) {
                var startIdx = Math.floor(Math.random() * mapData.airports.length);
                var endIdx = startIdx;
                do {
                    endIdx = Math.floor(Math.random() * mapData.airports.length);
                } while (endIdx === startIdx);

                var airplaneId = randomPlaneCode();
                routes[airplaneId] = { 
                    route: { 
                        from: mapData.airports[startIdx].pos, 
                        to: mapData.airports[endIdx].pos,
                        progress: 0
                    }
                };
                var lat = mapData.airports[startIdx].pos.lat;
                var lon = mapData.airports[startIdx].pos.lon;
                atcModel.addUpdateAirplane(airplaneId, lat, lon, getCurrentRegion(lat, lon));
            }

            // Update all routes
            for (var id in routes) {
                if (!routes.hasOwnProperty(id)) continue;
                if (airplanes[id] === undefined) continue;

                var plane = routes[id];
                plane.route.progress += 0.01; // adjust speed

                if (plane.route.progress >= 1) {
                    atcModel.removeAirplane(id);
                    delete routes[id];
                } else {
                    var lat = plane.route.from.lat + (plane.route.to.lat - plane.route.from.lat) * plane.route.progress;
                    var lon = plane.route.from.lon + (plane.route.to.lon - plane.route.from.lon) * plane.route.progress;
                    atcModel.addUpdateAirplane(id, lat, lon, getCurrentRegion(lat, lon));
                }
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        onClicked: {
            mapView.paused = !mapView.paused
            if (mapView.paused) {
                //shapesDemoModel.pause()
            } else {
                //shapesDemoModel.resume()
            }
        }
    }

    Label {
        text: "Paused"
        visible: mapView.paused
        anchors.top: parent.top
        anchors.right: parent.right
        font.pixelSize: 24
        anchors.margins: 10
    }
}
