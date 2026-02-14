// CenteredTabButton.qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

TabButton {
    id: control
    property alias tabText: label.text

    height: parent.height
    width: 150

    anchors.top: parent.top
    anchors.bottom: parent.bottom

    background: Rectangle {
        color: control.checked ? (rootWindow.isDarkMode ? "black" : "#ffffff") : (control.hovered ? (rootWindow.isDarkMode ? "#454545" : "#c9c7c7") : (rootWindow.isDarkMode ? "#383838" : "#dcdcdc"))
        
        //border.color: rootWindow.isDarkMode ? "#1e1e1e" : "#b9b9b9"
        //border.width: 1

        Rectangle {
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.right: parent.right
            width: 1
            color: rootWindow.isDarkMode ? "#1e1e1e" : "#b9b9b9"
        }


        // Blue top line indicator
        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 3                      // ⬅ thickness of the line
            color: "#144fff"               // ⬅ your blue color
            visible: control.checked        // only show when active
        }
    }
    // Use RowLayout to control padding
    contentItem: RowLayout {
        anchors.fill: parent
        anchors.margins: 0
        spacing: 0

        Label {
            id: label
            text: control.tabText
            font.pixelSize: 16

            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            Layout.leftMargin: 16      // ✅ actual padding from left
        }
    }
}
