# 本機驗證 — 2026-09-05

[English](../verification.md) | 繁體中文

驗證環境為 macOS 14.5 / arm64、Python 3.14.3、CMake 4.3.1、Ninja 1.13.0，以及 Homebrew Clang 22.1.2 / libc++ 220102。指令明確選用 `CXX=/opt/homebrew/opt/llvm/bin/clang++`。

## 結果

- 27 項工具與狀態行為測試通過。預設測試套件找到 30 項測試，並刻意略過三項需明確啟用的 C++ 整合測試。
- 三項 C++ 整合測試均在各自的驗證執行中通過：完整學習循環與程序重啟、刻意編譯錯誤的除錯，以及在隔離環境中以 debug 與 ASan+UBSan 重新檢查歷史完成快照。
- 完整循環測試驗證參考實作、debug 與 ASan 驗證、變異缺陷偵測、骨架失敗、不覆寫的學習者檢查、協助紀錄、模擬學習者修正、說明與審查、刪除可丟棄日誌，以及在新 Python 程序中復原。
- Doctor 的基準、ASan+UBSan 與 TSan 能力探測，均使用所選 LLVM 通過。這不代表並行練習的正確性已獲驗證。
- 選用本機編譯器並讓虛擬環境的 Ninja 可由 PATH 找到後，空白根目錄的 CMake 設定成功。
- 重複初始化沒有建立檔案，並保留工作階段版本 0。狀態顯示 onboarding、未選取練習，且無完整性問題。
- 在沒有已發布或已完成練習時，本機 `ci` 指令成功。Linux Clang/GCC GitHub Actions 已設定，但尚未在遠端執行。

預設 Apple Clang 安裝找不到 `iostream`；它不是已驗證的工具鏈。沒有替換系統編譯器。實作期間未建立正式練習或學習者能力觀察；C++ 驗證使用暫存測試夾具工作區。本機 Git 中繼資料已初始化，沒有提交或遠端發布。

## 重現

```sh
uv sync --frozen
source .venv/bin/activate
export CXX=/opt/homebrew/opt/llvm/bin/clang++
python tools/lab.py doctor
python -m unittest discover -s tools/tests -v
LAB_CPP_TESTS=1 python -m unittest discover -s tools/tests -v
python tools/lab.py status
```

在其他機器上，請使用適當的編譯器路徑。真正的整合測試首次需要取得固定版本的 Catch2 原始碼。工具測試不需要模型 API 或網路。
