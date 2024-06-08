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


SplitView {
    orientation: Qt.Horizontal

    property var childView

    Rectangle {
        id: domainSplit
        implicitWidth: 350
        SplitView.minimumWidth: 50
        color: rootWindow.isDarkMode ? Constants.darkOverviewBackground : Constants.lightOverviewBackground

        TopicOverview {}
    }
    Rectangle {
        id: centerItem
        SplitView.minimumWidth: 50
        SplitView.fillWidth: true
        color: rootWindow.isDarkMode ? Constants.darkMainContentBackground : Constants.lightMainContentBackground

        StackView {
            id: stackView
            anchors.fill: parent

        }
    }

    function showTopicEndpointView(domainId, topicName) {
        stackView.clear()
        if (childView) {
            childView.destroy()
        }
        var childComponent = Qt.createComponent("qrc:/src/views/TopicEndpointView.qml")
        if (childComponent.status === Component.Ready) {
            childView = childComponent.createObject(
                        stackView, {
                            domainId: domainId,
                            topicName: topicName
                        });
            stackView.replace(childView);
        } else {
            console.log("Failed to create component TopicEndpointView")
        }
    }
}
