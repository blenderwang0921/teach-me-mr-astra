# 本機格式化

[English](../formatting.md) | 繁體中文

`uv sync --frozen` 安裝鎖定版本的 Ruff 開發相依套件。`./lab format` 格式化框架 Python；`./lab format --check` 只檢查、不修改。也可明確指定檔案或目錄，包括 C++：`./lab format exercises/ID .instructor/ID`。目錄會遞迴選取符合條件的原始碼、忽略其他檔案類型，並回報略過的受保護原始碼數量。明確指定受保護或不存在的檔案仍會報錯。C++ 使用已安裝的 clang-format 與 `.clang-format`；不執行 lint 修正或模型呼叫。

VS Code 工作區設定為 Python（Ruff 擴充套件）與 C++（Microsoft C/C++ 擴充套件）啟用存檔時格式化。若尚未安裝，請一次安裝建議的擴充套件。儲存庫的 `.codex/hooks.json` 為 `apply_patch` 設定同步 PostToolUse 指令。它只格式化修補目標，成功時不輸出，失敗時回報錯誤。本機 Codex CLI 0.153.4 回報 hooks 已啟用。新的 Codex 工作階段必須載入設定；處理程式可在不呼叫模型的情況下測試。

此 hook 不涵蓋任意 shell 寫入、MCP 編輯器或其他編輯器中的手動修改。代理編輯應優先使用 `apply_patch`，讓 hook 能立即執行。對尚未發布的新題目（沒有 `ready.json`），`./lab prepare` 會在計算合約雜湊、建立快照及驗證前，自動同步格式化工作區與教師原始碼。因此 shell 產檔也不需另外執行格式化指令。若工作區有任何可編輯檔案與教師骨架不同，即使沒有發布標記，也會將整個工作區視為學習者實作而保留。格式化失敗會停止準備。已發布題目不會由 prepare 自動格式化；`check` 不會改寫學習者實作。不要使用非同步格式化工具：它可能在測試開始後，使測試快照失效。成功的本機格式化不使用模型推論；但 hook 中繼資料或錯誤訊息仍可能增加上下文，因此無法承諾整個工作階段的用量完全為零。

輔助工具會拒絕證據、報告、學習者紀錄、符號連結，以及已發布的教師檔案或提供檔案。既有學習者實作只有在透過檔案或目錄明確選取，或被修補編輯時才會格式化。Hook 不授予解題權限。編輯器的存檔時格式化只作用於正在儲存的文件；證據已設為唯讀。不要任意編輯已發布的提供檔案。

來源：[Codex hooks](https://learn.chatgpt.com/docs/hooks)、
[Ruff 編輯器設定](https://docs.astral.sh/ruff/editors/setup/)、
[VS Code C++ 格式化](https://code.visualstudio.com/docs/cpp/cpp-ide)。
