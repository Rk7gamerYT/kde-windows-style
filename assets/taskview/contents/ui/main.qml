// Windows 11 Task view button: opens KWin's overview of all windows and desktops (Win + Tab).
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.plasma.plasma5support as P5Support
import org.kde.plasma.plasmoid

PlasmoidItem {
    id: root
    preferredRepresentation: fullRepresentation
    toolTipMainText: i18n("Visão de tarefas")
    toolTipSubText: i18n("Win + Tab")

    P5Support.DataSource {
        id: shell
        engine: "executable"
        onNewData: source => disconnectSource(source)
    }

    fullRepresentation: MouseArea {
        id: button
        Layout.minimumWidth: height
        Layout.maximumWidth: height
        Layout.fillHeight: true
        hoverEnabled: true
        onClicked: shell.connectSource("qdbus6 org.kde.kglobalaccel /component/kwin org.kde.kglobalaccel.Component.invokeShortcut Overview # " + Date.now())

        Rectangle {
            anchors.fill: parent
            anchors.margins: Kirigami.Units.smallSpacing
            radius: Kirigami.Units.cornerRadius
            color: Kirigami.Theme.textColor
            opacity: button.pressed ? 0.12 : button.containsMouse ? 0.07 : 0
        }

        // Two overlapping windows, drawn so the button matches Windows without a bundled image.
        Item {
            anchors.centerIn: parent
            width: Kirigami.Units.iconSizes.smallMedium
            height: width
            Rectangle {
                x: parent.width * 0.3; y: 0
                width: parent.width * 0.7; height: parent.height * 0.7
                radius: 2
                color: Kirigami.Theme.textColor
                opacity: 0.55
            }
            Rectangle {
                x: 0; y: parent.height * 0.3
                width: parent.width * 0.7; height: parent.height * 0.7
                radius: 2
                color: Kirigami.Theme.textColor
                border.width: 1
                border.color: Kirigami.Theme.backgroundColor
            }
        }
    }
}
