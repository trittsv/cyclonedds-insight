import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    width: 390
    height: 720
    visible: true
    title: "Insight Android Probe"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 20

        Label {
            text: "CycloneDDS Insight"
            font.pixelSize: 26
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
        Label {
            text: "Android deployment probe"
            font.pixelSize: 20
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
        Label {
            text: ddsProbe.status
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
        Button {
            text: ddsProbe.running ? "Stop DDS" : "Start DDS (domain 0)"
            onClicked: ddsProbe.running ? ddsProbe.stop() : ddsProbe.start()
            Layout.fillWidth: true
        }
        Button {
            text: "Send sample"
            enabled: ddsProbe.running
            onClicked: ddsProbe.send()
            Layout.fillWidth: true
        }
        Button {
            property int taps: 0
            text: "Touch test: " + taps
            onClicked: taps++
            Layout.fillWidth: true
        }
        Item { Layout.fillHeight: true }
    }
}
