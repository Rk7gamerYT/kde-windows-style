// Windows 11 style weather on the taskbar: icon, temperature and condition, with a short forecast.
// Data from Open-Meteo (free, no key): https://open-meteo.com
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.plasmoid

PlasmoidItem {
    id: root

    readonly property string city: Plasmoid.configuration.city
    readonly property bool fahrenheit: Plasmoid.configuration.fahrenheit
    property string place: ""
    property var current: null
    property var daily: null
    property string error: ""

    // WMO weather codes: [day icon, night icon, description]
    readonly property var codes: ({
        0: ["weather-clear", "weather-clear-night", i18n("Ensolarado")],
        1: ["weather-few-clouds", "weather-few-clouds-night", i18n("Predominantemente limpo")],
        2: ["weather-few-clouds", "weather-few-clouds-night", i18n("Parcialmente nublado")],
        3: ["weather-overcast", "weather-overcast", i18n("Nublado")],
        45: ["weather-fog", "weather-fog", i18n("Neblina")],
        48: ["weather-fog", "weather-fog", i18n("Neblina")],
        51: ["weather-showers-scattered", "weather-showers-scattered-night", i18n("Garoa")],
        53: ["weather-showers-scattered", "weather-showers-scattered-night", i18n("Garoa")],
        55: ["weather-showers-scattered", "weather-showers-scattered-night", i18n("Garoa")],
        61: ["weather-showers", "weather-showers-night", i18n("Chuva fraca")],
        63: ["weather-showers", "weather-showers-night", i18n("Chuva")],
        65: ["weather-showers", "weather-showers-night", i18n("Chuva forte")],
        66: ["weather-freezing-rain", "weather-freezing-rain", i18n("Chuva congelante")],
        67: ["weather-freezing-rain", "weather-freezing-rain", i18n("Chuva congelante")],
        71: ["weather-snow", "weather-snow", i18n("Neve")],
        73: ["weather-snow", "weather-snow", i18n("Neve")],
        75: ["weather-snow", "weather-snow", i18n("Neve forte")],
        80: ["weather-showers-scattered", "weather-showers-scattered-night", i18n("Pancadas de chuva")],
        81: ["weather-showers", "weather-showers-night", i18n("Pancadas de chuva")],
        82: ["weather-storm", "weather-storm-night", i18n("Pancadas fortes")],
        95: ["weather-storm", "weather-storm-night", i18n("Tempestade")],
        96: ["weather-storm", "weather-storm-night", i18n("Tempestade com granizo")],
        99: ["weather-storm", "weather-storm-night", i18n("Tempestade com granizo")]
    })

    function icon(code, day) { const c = codes[code] || codes[3]; return day ? c[0] : c[1] }
    function describe(code) { return (codes[code] || codes[3])[2] }
    function degrees(value) { return Math.round(value) + (fahrenheit ? "°F" : "°C") }

    function get(url, done) {
        const request = new XMLHttpRequest()
        request.onreadystatechange = () => {
            if (request.readyState !== XMLHttpRequest.DONE) return
            if (request.status === 200) {
                try { done(JSON.parse(request.responseText)); error = "" } catch (e) { error = i18n("Resposta inválida") }
            } else {
                error = i18n("Sem conexão")
            }
        }
        request.open("GET", url)
        request.send()
    }

    function refresh() {
        if (!city) { error = i18n("Escolha uma cidade"); return }
        get("https://geocoding-api.open-meteo.com/v1/search?count=1&language=pt&name=" + encodeURIComponent(city), result => {
            const found = (result.results || [])[0]
            if (!found) { error = i18n("Cidade não encontrada"); return }
            place = found.name
            get("https://api.open-meteo.com/v1/forecast?latitude=" + found.latitude + "&longitude=" + found.longitude
                + "&current=temperature_2m,weather_code,is_day,apparent_temperature,relative_humidity_2m"
                + "&daily=weather_code,temperature_2m_max,temperature_2m_min&forecast_days=5&timezone=auto"
                + (fahrenheit ? "&temperature_unit=fahrenheit" : ""), forecast => {
                current = forecast.current
                daily = forecast.daily
            })
        })
    }

    onCityChanged: refresh()
    onFahrenheitChanged: refresh()
    Timer { interval: 20 * 60 * 1000; running: true; repeat: true; triggeredOnStart: true; onTriggered: root.refresh() }

    preferredRepresentation: compactRepresentation
    Plasmoid.icon: current ? icon(current.weather_code, current.is_day) : "weather-none-available"
    toolTipMainText: current ? place + " · " + degrees(current.temperature_2m) : i18n("Clima")
    toolTipSubText: current ? describe(current.weather_code) : error

    compactRepresentation: MouseArea {
        id: compact
        Layout.minimumWidth: row.implicitWidth + Kirigami.Units.largeSpacing * 2
        hoverEnabled: true
        onClicked: root.expanded = !root.expanded

        Rectangle {
            anchors.fill: parent
            anchors.topMargin: Kirigami.Units.smallSpacing
            anchors.bottomMargin: Kirigami.Units.smallSpacing
            radius: Kirigami.Units.cornerRadius
            color: Kirigami.Theme.textColor
            opacity: root.expanded ? 0.12 : compact.containsMouse ? 0.07 : 0
        }

        RowLayout {
            id: row
            anchors.centerIn: parent
            spacing: Kirigami.Units.smallSpacing * 2
            Kirigami.Icon {
                source: Plasmoid.icon
                implicitWidth: Kirigami.Units.iconSizes.medium; implicitHeight: implicitWidth
            }
            ColumnLayout {
                spacing: 0
                PlasmaComponents3.Label {
                    text: root.current ? root.degrees(root.current.temperature_2m) : "--"
                    font: Kirigami.Theme.smallFont
                }
                PlasmaComponents3.Label {
                    text: root.current ? root.describe(root.current.weather_code) : root.error
                    font: Kirigami.Theme.smallFont
                    opacity: 0.8
                }
            }
        }
    }

    fullRepresentation: ColumnLayout {
        Layout.preferredWidth: Kirigami.Units.gridUnit * 20
        Layout.minimumWidth: Layout.preferredWidth
        spacing: Kirigami.Units.largeSpacing

        RowLayout {
            Layout.margins: Kirigami.Units.largeSpacing
            spacing: Kirigami.Units.largeSpacing
            Kirigami.Icon {
                source: Plasmoid.icon
                implicitWidth: Kirigami.Units.iconSizes.huge; implicitHeight: implicitWidth
            }
            ColumnLayout {
                spacing: 0
                Kirigami.Heading { text: root.current ? root.degrees(root.current.temperature_2m) : "--"; level: 1 }
                PlasmaComponents3.Label { text: root.current ? root.describe(root.current.weather_code) : root.error }
                PlasmaComponents3.Label {
                    visible: !!root.current
                    opacity: 0.7
                    text: root.current ? i18n("Sensação de %1 · Umidade %2%", root.degrees(root.current.apparent_temperature),
                                              root.current.relative_humidity_2m) : ""
                }
                PlasmaComponents3.Label { text: root.place; opacity: 0.7 }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: Kirigami.Units.largeSpacing
            Layout.rightMargin: Kirigami.Units.largeSpacing
            visible: !!root.daily
            Repeater {
                model: root.daily ? root.daily.time.length : 0
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing
                    PlasmaComponents3.Label {
                        Layout.alignment: Qt.AlignHCenter
                        text: index === 0 ? i18n("Hoje")
                            : Qt.locale().dayName(new Date(root.daily.time[index] + "T12:00").getDay(), Locale.ShortFormat)
                    }
                    Kirigami.Icon {
                        Layout.alignment: Qt.AlignHCenter
                        source: root.icon(root.daily.weather_code[index], true)
                        implicitWidth: Kirigami.Units.iconSizes.medium; implicitHeight: implicitWidth
                    }
                    PlasmaComponents3.Label {
                        Layout.alignment: Qt.AlignHCenter
                        text: Math.round(root.daily.temperature_2m_max[index]) + "° " + Math.round(root.daily.temperature_2m_min[index]) + "°"
                        font: Kirigami.Theme.smallFont
                    }
                }
            }
        }

        PlasmaComponents3.Label {
            Layout.margins: Kirigami.Units.largeSpacing
            Layout.alignment: Qt.AlignRight
            text: i18n("Dados: Open-Meteo")
            font: Kirigami.Theme.smallFont
            opacity: 0.6
        }
    }
}
