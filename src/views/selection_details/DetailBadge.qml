/*
 * Copyright(c) 2026 Sven Trittler
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
 */

pragma ComponentBehavior: Bound

import QtQuick

Rectangle {
    id: badge

    property string kind: "participant"
    readonly property color iconColor: "#274ff6"

    implicitWidth: 24
    implicitHeight: 24
    radius: 7
    color: rootWindow.isDarkMode ? "#17254f" : "#e6ebff"

    Loader {
        anchors.centerIn: parent
        sourceComponent: {
            if (badge.kind === "domain")
                return domainIcon
            if (badge.kind === "host")
                return hostIcon
            if (badge.kind === "process")
                return processIcon
            if (badge.kind === "topic")
                return topicIcon
            if (badge.kind === "endpoint")
                return endpointIcon
            if (badge.kind === "statistics")
                return statisticsIcon
            if (badge.kind === "tester")
                return testerIcon
            if (badge.kind === "listener")
                return listenerIcon
            if (badge.kind === "details")
                return detailsIcon
            if (badge.kind === "settings")
                return settingsIcon
            if (badge.kind === "configuration")
                return configurationIcon
            if (badge.kind === "shapes")
                return shapesIcon
            return participantIcon
        }
    }

    Component {
        id: participantIcon

        Item {
            width: 12
            height: 14

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 6
                height: 6
                radius: 3
                color: badge.iconColor
            }

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                width: 12
                height: 7
                radius: 3.5
                color: badge.iconColor
            }
        }
    }

    Component {
        id: domainIcon

        Item {
            width: 14
            height: 14

            Rectangle {
                x: 3
                y: 3
                width: 8
                height: 1.5
                rotation: 30
                color: badge.iconColor
            }

            Rectangle {
                x: 3
                y: 9
                width: 8
                height: 1.5
                rotation: -30
                color: badge.iconColor
            }

            Repeater {
                model: [[1, 5], [9, 1], [9, 9]]

                Rectangle {
                    required property var modelData
                    x: modelData[0]
                    y: modelData[1]
                    width: 4
                    height: 4
                    radius: 2
                    color: badge.iconColor
                }
            }
        }
    }

    Component {
        id: hostIcon

        Item {
            width: 14
            height: 13

            Rectangle {
                width: 14
                height: 9
                radius: 2
                color: "transparent"
                border.width: 1.5
                border.color: badge.iconColor
            }

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                y: 9
                width: 2
                height: 3
                color: badge.iconColor
            }

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                width: 8
                height: 1.5
                radius: 0.75
                color: badge.iconColor
            }
        }
    }

    Component {
        id: processIcon

        Item {
            width: 14
            height: 13

            Repeater {
                model: [0, 5, 10]

                Item {
                    required property int modelData
                    y: modelData
                    width: 14
                    height: 3

                    Rectangle {
                        width: 3
                        height: 3
                        radius: 1.5
                        color: badge.iconColor
                    }

                    Rectangle {
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        width: 9
                        height: 1.5
                        radius: 0.75
                        color: badge.iconColor
                    }
                }
            }
        }
    }

    Component {
        id: topicIcon

        Item {
            width: 14
            height: 13

            Rectangle {
                width: 14
                height: 11
                radius: 3
                color: "transparent"
                border.width: 1.5
                border.color: badge.iconColor
            }

            Rectangle {
                x: 3
                y: 4
                width: 8
                height: 1.5
                radius: 0.75
                color: badge.iconColor
            }

            Rectangle {
                x: 3
                y: 7
                width: 6
                height: 1.5
                radius: 0.75
                color: badge.iconColor
            }
        }
    }

    Component {
        id: endpointIcon

        Item {
            width: 14
            height: 12

            Rectangle {
                anchors.centerIn: parent
                width: 8
                height: 1.5
                color: badge.iconColor
            }

            Rectangle {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                width: 5
                height: 5
                radius: 2.5
                color: badge.iconColor
            }

            Rectangle {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                width: 5
                height: 5
                radius: 2.5
                color: badge.iconColor
            }
        }
    }

    Component {
        id: statisticsIcon

        Item {
            width: 14
            height: 14

            Rectangle {
                x: 1
                y: 1
                width: 1.5
                height: 12
                color: badge.iconColor
            }

            Rectangle {
                x: 1
                y: 11.5
                width: 12
                height: 1.5
                color: badge.iconColor
            }

            Rectangle {
                x: 2
                y: 8
                width: 5
                height: 1.5
                radius: 0.75
                rotation: -35
                transformOrigin: Item.Left
                color: badge.iconColor
            }

            Rectangle {
                x: 6
                y: 5.5
                width: 4
                height: 1.5
                radius: 0.75
                rotation: 24
                transformOrigin: Item.Left
                color: badge.iconColor
            }

            Rectangle {
                x: 9
                y: 7
                width: 5
                height: 1.5
                radius: 0.75
                rotation: -52
                transformOrigin: Item.Left
                color: badge.iconColor
            }
        }
    }

    Component {
        id: testerIcon

        Item {
            width: 14
            height: 12

            Rectangle {
                x: 0
                y: 2
                width: 7
                height: 8
                radius: 2
                color: "transparent"
                border.width: 1.5
                border.color: badge.iconColor
            }

            Rectangle {
                x: 2
                y: 5
                width: 3
                height: 1.5
                radius: 0.75
                color: badge.iconColor
            }

            Rectangle {
                x: 7
                anchors.verticalCenter: parent.verticalCenter
                width: 4
                height: 1.5
                radius: 0.75
                color: badge.iconColor
            }

            Rectangle {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                width: 5
                height: 5
                radius: 2.5
                color: badge.iconColor
            }
        }
    }

    Component {
        id: listenerIcon

        Item {
            width: 14
            height: 12

            Rectangle {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                width: 5
                height: 5
                radius: 2.5
                color: badge.iconColor
            }

            Rectangle {
                x: 4
                anchors.verticalCenter: parent.verticalCenter
                width: 4
                height: 1.5
                radius: 0.75
                color: badge.iconColor
            }

            Rectangle {
                x: 7
                y: 2
                width: 7
                height: 8
                radius: 2
                color: "transparent"
                border.width: 1.5
                border.color: badge.iconColor
            }

            Rectangle {
                x: 9
                y: 5
                width: 3
                height: 1.5
                radius: 0.75
                color: badge.iconColor
            }
        }
    }

    Component {
        id: detailsIcon

        Item {
            width: 13
            height: 14

            Rectangle {
                width: 13
                height: 14
                radius: 2
                color: "transparent"
                border.width: 1.5
                border.color: badge.iconColor
            }

            Repeater {
                model: [4, 7, 10]

                Rectangle {
                    required property int modelData
                    x: 3
                    y: modelData
                    width: 7
                    height: 1.5
                    radius: 0.75
                    color: badge.iconColor
                }
            }
        }
    }

    Component {
        id: settingsIcon

        Item {
            width: 14
            height: 14

            Repeater {
                model: [[2, 3, 8], [2, 7, 4], [2, 11, 9]]

                Item {
                    required property var modelData
                    x: modelData[0]
                    y: modelData[1]
                    width: 12
                    height: 2

                    Rectangle {
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width
                        height: 1.5
                        radius: 0.75
                        color: badge.iconColor
                    }

                    Rectangle {
                        x: modelData[2]
                        anchors.verticalCenter: parent.verticalCenter
                        width: 4
                        height: 4
                        radius: 2
                        color: badge.iconColor
                    }
                }
            }
        }
    }

    Component {
        id: configurationIcon

        Item {
            width: 14
            height: 14

            Rectangle {
                width: 14
                height: 14
                radius: 2
                color: "transparent"
                border.width: 1.5
                border.color: badge.iconColor
            }

            Repeater {
                model: [[3, 4, 5], [3, 8, 8]]

                Item {
                    required property var modelData
                    x: modelData[0]
                    y: modelData[1]
                    width: 9
                    height: 2

                    Rectangle {
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width
                        height: 1.5
                        radius: 0.75
                        color: badge.iconColor
                    }

                    Rectangle {
                        x: modelData[2]
                        anchors.verticalCenter: parent.verticalCenter
                        width: 4
                        height: 4
                        radius: 2
                        color: badge.iconColor
                    }
                }
            }
        }
    }

    Component {
        id: shapesIcon

        Item {
            width: 14
            height: 14

            Rectangle {
                x: 1
                y: 1
                width: 6
                height: 6
                radius: 3
                color: badge.iconColor
            }

            Rectangle {
                x: 7
                y: 7
                width: 6
                height: 6
                radius: 1
                color: badge.iconColor
            }

            Canvas {
                anchors.fill: parent

                onPaint: {
                    const context = getContext("2d")
                    context.clearRect(0, 0, width, height)
                    context.fillStyle = badge.iconColor
                    context.beginPath()
                    context.moveTo(9.5, 1)
                    context.lineTo(13, 6.5)
                    context.lineTo(6, 6.5)
                    context.closePath()
                    context.fill()
                }
            }
        }
    }
}
