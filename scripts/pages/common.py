"""Texts both pages use."""
from lib import reg


def register():
    reg("copy", "Copy", "複製", "コピー")
    reg("zoom", "Enlarge", "放大檢視", "拡大表示")
    reg("zm_fit", "Fit", "符合視窗", "ウィンドウに合わせる")
    reg("open_full", "Open full size", "開啟原尺寸", "原寸で開く")
    reg("changelog", "Changelog", "變更紀錄", "変更履歴")
    reg("copied", "Copied", "已複製", "コピーしました")
    reg("nav_home", "Home", "首頁", "ホーム")
    reg("nav_how", "How it works", "運作架構", "仕組み")
    reg("disc",
        "jt-glogarch is provided “as is” without warranty of any kind (AGPL-3.0, sections 15 and 16). You are responsible "
        "for testing it in your own environment before relying on it, and for keeping your own copies of what matters. "
        "Graylog and OpenSearch are trademarks of their respective owners; this project is not affiliated with them.",
        "jt-glogarch 依「現狀」提供，不附任何保證（AGPL-3.0 第 15、16 條）；正式使用前請自行在您的環境測試，重要資料請另行保留複本。"
        "Graylog 與 OpenSearch 為各自所有者的商標，本專案與其無隸屬關係。",
        "jt-glogarch は「現状のまま」提供され、いかなる保証もありません（AGPL-3.0 第 15・16 条）。本番で使う前にご自身の環境でテストし、"
        "重要なデータは別途コピーを保管してください。Graylog と OpenSearch は各所有者の商標であり、本プロジェクトはそれらと提携していません。")
