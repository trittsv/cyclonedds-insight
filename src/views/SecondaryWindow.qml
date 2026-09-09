import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: secondaryWindow
    readonly property bool mobileWindow: Qt.platform.os === "android"

    // Fill the available screen without hiding Android's system bars.
    // Apply on every opening, including callers that only set visible = true.
    onVisibleChanged: {
        if (mobileWindow && visible)
            showMaximized()
    }

    header: ToolBar {
        id: closeToolBar
        visible: secondaryWindow.mobileWindow
        height: visible ? implicitHeight : 0
        topPadding: mobileWindow ? SafeArea.margins.top : 0
        leftPadding: 12 + (mobileWindow ? SafeArea.margins.left : 0)
        rightPadding: mobileWindow ? SafeArea.margins.right : 0
        contentItem: RowLayout {
            Label {
                text: secondaryWindow.title
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
            ToolButton {
                id: closeButton
                implicitWidth: 48
                implicitHeight: 48
                contentItem: Item {
                    // Draw the icon without relying on Android's font glyphs.
                    Rectangle {
                        anchors.centerIn: parent
                        width: 20
                        height: 2
                        rotation: 45
                        color: closeButton.palette.buttonText
                        antialiasing: true
                    }
                    Rectangle {
                        anchors.centerIn: parent
                        width: 20
                        height: 2
                        rotation: -45
                        color: closeButton.palette.buttonText
                        antialiasing: true
                    }
                }
                Accessible.name: qsTr("Close window")
                onClicked: secondaryWindow.close()
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Close window")
            }
        }
    }

    Shortcut {
        sequence: "Back"
        enabled: secondaryWindow.mobileWindow && secondaryWindow.visible
        onActivated: secondaryWindow.close()
    }
}
