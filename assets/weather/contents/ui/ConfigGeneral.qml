import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCM

KCM.SimpleKCM {
    property alias cfg_city: city.text
    property alias cfg_fahrenheit: fahrenheit.checked

    Kirigami.FormLayout {
        QQC2.TextField {
            id: city
            Kirigami.FormData.label: i18n("Cidade:")
            placeholderText: i18n("Ex.: São Paulo")
        }
        QQC2.CheckBox {
            id: fahrenheit
            Kirigami.FormData.label: i18n("Unidade:")
            text: i18n("Fahrenheit (°F)")
        }
    }
}
