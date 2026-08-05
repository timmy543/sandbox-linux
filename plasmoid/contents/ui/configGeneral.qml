import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kcmutils as KCM
import org.kde.kirigami as Kirigami

KCM.SimpleKCM {
    property alias cfg_fontSize: fontSize.value

    Kirigami.FormLayout {
        anchors.fill: parent

        QQC2.SpinBox {
            id: fontSize
            Kirigami.FormData.label: i18n("Velikost písma:")
            from: 0
            to: 48
            textFromValue: function (value) {
                return value === 0 ? i18n("systémová") : value + " pt";
            }
            valueFromText: function (text) {
                return parseInt(text) || 0;
            }
        }
    }
}
