// Windows 11 style quick settings: one taskbar button for network, sound and battery,
// opening a flyout with toggle tiles and a volume slider.
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasma5support as P5Support
import org.kde.plasma.plasmoid

PlasmoidItem {
    id: root

    property var info: ({})
    readonly property bool wired: info.wired > 0
    readonly property bool wifiOn: info.wifi === "enabled"
    readonly property bool btOn: info.bt === "yes"
    readonly property bool hasBluetooth: info.hasbt > 0
    readonly property bool airplane: info.airplane === "yes"
    readonly property bool muted: info.mute === "yes"
    readonly property bool nightLight: info.night === "true"
    readonly property bool doNotDisturb: (info.dnd || "") !== ""
    readonly property int volume: parseInt(info.volume || "0")
    readonly property string statusScript: Qt.resolvedUrl("../code/status.sh").toString().replace("file://", "")

    readonly property var battery: power.data["Battery"] || {}
    readonly property bool hasBattery: battery["Has Battery"] === true
    readonly property int batteryPercent: battery["Percent"] || 0

    readonly property string networkIcon: wired ? "network-wired-activated"
        : airplane ? "network-flightmode-on"
        : !wifiOn ? "network-wireless-disconnected"
        : info.ssid ? "network-wireless-signal-excellent" : "network-wireless-disconnected"
    readonly property string volumeIcon: muted || volume === 0 ? "audio-volume-muted"
        : volume < 34 ? "audio-volume-low" : volume < 67 ? "audio-volume-medium" : "audio-volume-high"

    preferredRepresentation: compactRepresentation
    Plasmoid.icon: volumeIcon
    toolTipMainText: i18n("Configurações rápidas")
    toolTipSubText: (wired ? i18n("Ethernet") : info.ssid || i18n("Sem internet")) + " · " + i18n("Volume: %1%", volume)
        + (hasBattery ? " · " + i18n("Bateria: %1%", batteryPercent) : "")

    P5Support.DataSource {
        id: shell
        engine: "executable"
        onNewData: (source, data) => {
            disconnectSource(source)
            if (source === root.statusScript) {
                const next = {}
                for (const pair of (data["stdout"] || "").trim().split("|")) {
                    const at = pair.indexOf("=")
                    if (at > 0) next[pair.slice(0, at)] = pair.slice(at + 1)
                }
                root.info = next
            }
        }
    }

    P5Support.DataSource {
        id: power
        engine: "powermanagement"
        connectedSources: ["Battery"]
    }

    function refresh() { shell.connectSource(statusScript) }
    function run(command) {
        // A unique suffix lets the same command run twice in a row.
        shell.connectSource(command + " # " + Date.now())
        refreshSoon.restart()
    }

    Timer { interval: root.expanded ? 2000 : 5000; running: true; repeat: true; triggeredOnStart: true; onTriggered: root.refresh() }
    Timer { id: refreshSoon; interval: 500; onTriggered: root.refresh() }
    Timer {
        id: applyVolume
        interval: 80
        property int value
        onTriggered: root.run("pactl set-sink-mute @DEFAULT_SINK@ 0; pactl set-sink-volume @DEFAULT_SINK@ " + value + "%")
    }

    compactRepresentation: MouseArea {
        id: compact
        Layout.minimumWidth: icons.implicitWidth + Kirigami.Units.largeSpacing * 2
        hoverEnabled: true
        onClicked: root.expanded = !root.expanded
        onWheel: wheel => {
            const value = Math.max(0, Math.min(100, root.volume + (wheel.angleDelta.y > 0 ? 2 : -2)))
            root.info = Object.assign({}, root.info, {volume: String(value)})
            applyVolume.value = value; applyVolume.restart()
        }

        Rectangle {
            anchors.fill: parent
            anchors.topMargin: Kirigami.Units.smallSpacing
            anchors.bottomMargin: Kirigami.Units.smallSpacing
            radius: Kirigami.Units.cornerRadius
            color: Kirigami.Theme.textColor
            opacity: root.expanded ? 0.12 : compact.containsMouse ? 0.07 : 0
        }

        RowLayout {
            id: icons
            anchors.centerIn: parent
            spacing: Kirigami.Units.smallSpacing * 2
            Kirigami.Icon { source: root.networkIcon; implicitWidth: Kirigami.Units.iconSizes.small; implicitHeight: implicitWidth }
            Kirigami.Icon { source: root.volumeIcon; implicitWidth: Kirigami.Units.iconSizes.small; implicitHeight: implicitWidth }
            Kirigami.Icon {
                visible: root.hasBattery
                source: "battery-" + String(Math.round(root.batteryPercent / 10) * 10).padStart(3, "0")
                implicitWidth: Kirigami.Units.iconSizes.small; implicitHeight: implicitWidth
            }
        }
    }

    fullRepresentation: ColumnLayout {
        Layout.preferredWidth: Kirigami.Units.gridUnit * 22
        Layout.minimumWidth: Layout.preferredWidth
        spacing: Kirigami.Units.largeSpacing

        GridLayout {
            Layout.fillWidth: true
            Layout.margins: Kirigami.Units.largeSpacing
            columns: 3
            columnSpacing: Kirigami.Units.largeSpacing
            rowSpacing: Kirigami.Units.largeSpacing

            Tile {
                text: root.wired ? i18n("Ethernet") : root.info.ssid || i18n("Wi-Fi")
                icon: root.wired ? "network-wired-activated" : root.wifiOn ? "network-wireless-signal-excellent" : "network-wireless-disconnected"
                checked: root.wired || root.wifiOn
                // On a cable there is no radio to switch, so the tile opens the network settings.
                onToggled: root.wired ? more() : root.run("nmcli radio wifi " + (root.wifiOn ? "off" : "on"))
                onMore: root.run("systemsettings kcm_networkmanagement")
            }
            Tile {
                visible: root.hasBluetooth
                text: i18n("Bluetooth")
                icon: root.btOn ? "network-bluetooth-activated" : "network-bluetooth-inactive"
                checked: root.btOn
                onToggled: root.run("bluetoothctl power " + (root.btOn ? "off" : "on"))
                onMore: root.run("systemsettings kcm_bluetooth")
            }
            Tile {
                text: i18n("Modo avião")
                icon: "network-flightmode-on"
                checked: root.airplane
                onToggled: root.run("rfkill " + (root.airplane ? "unblock" : "block") + " all")
            }
            Tile {
                text: i18n("Luz noturna")
                icon: "redshift-status-on"
                checked: root.nightLight
                onToggled: root.run(root.nightLight
                    ? "kwriteconfig6 --file kwinrc --group NightColor --key Active --notify --delete"
                    : "kwriteconfig6 --file kwinrc --group NightColor --key Active --notify true")
                onMore: root.run("systemsettings kcm_nightlight")
            }
            Tile {
                text: i18n("Não incomodar")
                icon: "notifications-disabled"
                checked: root.doNotDisturb
                onToggled: root.run(root.doNotDisturb
                    ? "kwriteconfig6 --file plasmanotifyrc --group DoNotDisturb --key Until --notify --delete"
                    : "kwriteconfig6 --file plasmanotifyrc --group DoNotDisturb --key Until --notify 2099,1,1,0,0,0")
            }
            Tile {
                text: i18n("Acessibilidade")
                icon: "preferences-desktop-accessibility"
                checked: false
                onToggled: root.run("systemsettings kcm_access")
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: Kirigami.Units.largeSpacing
            Layout.rightMargin: Kirigami.Units.largeSpacing
            PlasmaComponents3.ToolButton {
                icon.name: root.volumeIcon
                onClicked: root.run("pactl set-sink-mute @DEFAULT_SINK@ toggle")
                PlasmaComponents3.ToolTip { text: root.muted ? i18n("Ativar som") : i18n("Silenciar") }
            }
            PlasmaComponents3.Slider {
                Layout.fillWidth: true
                from: 0; to: 100; stepSize: 1
                value: root.volume
                onMoved: { applyVolume.value = Math.round(value); applyVolume.restart() }
            }
            PlasmaComponents3.Label { text: root.volume; Layout.minimumWidth: Kirigami.Units.gridUnit * 1.5; horizontalAlignment: Text.AlignRight }
            PlasmaComponents3.ToolButton {
                icon.name: "go-next"
                onClicked: root.run("systemsettings kcm_pulseaudio")
                PlasmaComponents3.ToolTip { text: i18n("Dispositivos de som") }
            }
        }

        // Footer strip, darker like the bottom of the Windows 11 flyout.
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: footer.implicitHeight + Kirigami.Units.largeSpacing * 2
            color: Qt.rgba(0, 0, 0, 0.15)
            RowLayout {
                id: footer
                anchors.fill: parent
                anchors.margins: Kirigami.Units.largeSpacing
                Kirigami.Icon {
                    visible: root.hasBattery
                    source: "battery-" + String(Math.round(root.batteryPercent / 10) * 10).padStart(3, "0")
                    implicitWidth: Kirigami.Units.iconSizes.small; implicitHeight: implicitWidth
                }
                PlasmaComponents3.Label { visible: root.hasBattery; text: root.batteryPercent + "%" }
                Item { Layout.fillWidth: true }
                PlasmaComponents3.ToolButton {
                    icon.name: "configure"
                    onClicked: { root.expanded = false; root.run("systemsettings") }
                    PlasmaComponents3.ToolTip { text: i18n("Todas as configurações") }
                }
            }
        }
    }

    component Tile: ColumnLayout {
        id: tile
        property alias text: caption.text
        property string icon
        property bool checked
        signal toggled()
        signal more()
        Layout.fillWidth: true
        spacing: Kirigami.Units.smallSpacing

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: Kirigami.Units.gridUnit * 2.6
            radius: Kirigami.Units.cornerRadius
            color: tile.checked ? Kirigami.Theme.highlightColor
                : Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, area.containsMouse ? 0.12 : 0.07)
            border.width: tile.checked ? 0 : 1
            border.color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.1)
            Kirigami.Icon {
                anchors.centerIn: parent
                source: tile.icon
                implicitWidth: Kirigami.Units.iconSizes.small; implicitHeight: implicitWidth
                color: tile.checked ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
                isMask: true
            }
            MouseArea {
                id: area
                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.LeftButton | Qt.RightButton
                cursorShape: Qt.PointingHandCursor
                onClicked: mouse => mouse.button === Qt.RightButton ? tile.more() : tile.toggled()
            }
        }
        PlasmaComponents3.Label {
            id: caption
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            font: Kirigami.Theme.smallFont
        }
    }
}
