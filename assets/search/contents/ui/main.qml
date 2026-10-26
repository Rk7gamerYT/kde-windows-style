// Windows 11 style search box on the taskbar. Like on Windows, it opens Start with the search field
// focused (Menu11 Next), so typing right away searches apps, files and settings.
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.plasma5support as P5Support
import org.kde.plasma.plasmoid

PlasmoidItem {
    id: root
    preferredRepresentation: fullRepresentation
    toolTipMainText: i18n("Pesquisar")
    toolTipSubText: i18n("Aplicativos, arquivos, configurações e a web")

    P5Support.DataSource {
        id: shell
        engine: "executable"
        onNewData: source => disconnectSource(source)
    }

    fullRepresentation: MouseArea {
        id: box
        Layout.minimumWidth: Kirigami.Units.gridUnit * 12
        Layout.maximumWidth: Layout.minimumWidth
        Layout.fillHeight: true
        hoverEnabled: true
        cursorShape: Qt.IBeamCursor
        onClicked: shell.connectSource("qdbus6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.activateLauncherMenu # " + Date.now())

        Rectangle {
            id: pill
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width
            height: Math.min(parent.height - Kirigami.Units.smallSpacing * 2, Kirigami.Units.gridUnit * 2)
            radius: height / 2
            color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, box.containsMouse ? 0.12 : 0.07)
            border.width: 1
            border.color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.12)

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Kirigami.Units.largeSpacing
                anchors.rightMargin: Kirigami.Units.largeSpacing
                spacing: Kirigami.Units.smallSpacing * 2
                Kirigami.Icon {
                    source: "search"
                    implicitWidth: Kirigami.Units.iconSizes.small; implicitHeight: implicitWidth
                }
                PlasmaComponents3.Label {
                    Layout.fillWidth: true
                    text: i18n("Pesquisar")
                    opacity: 0.75
                    elide: Text.ElideRight
                }
            }
        }
    }
}
