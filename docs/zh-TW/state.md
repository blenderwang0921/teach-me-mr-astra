# 狀態交易

[English](../state.md) | 繁體中文

所有結構化紀錄都使用 `schema_version: 1`。結構描述位於 `schemas/`；宣告介面以外的欄位會被拒絕。`session.version` 是樂觀並行控制計數器，與練習修訂版無關。

`state apply <file>` 接受 `schema_version`、`expected_version`，以及選填的 `profile`、`session`、`evidence` 和 `reviews`。Profile/session 是完整替換物件；evidence/reviews 則是新增紀錄。提供 session 時，將其版本設為 `expected_version + 1`。只有 evidence 或 profile 的交易，也會遞增儲存的工作階段版本。建立更新內容前，立即讀取 `status --json`。

`init` 後第一次轉換的範例：

```json
{
  "schema_version": 1,
  "expected_version": 0,
  "session": {
    "schema_version": 1,
    "version": 1,
    "phase": "planning",
    "current_exercise_id": null,
    "exercise_revision": null,
    "last_report_id": null,
    "pending_questions": [],
    "next_action": "Choose one short calibration task based on the saved interview.",
    "resume_phase": null,
    "reason": null,
    "completed_exercises": []
  }
}
```

儲存更新檔案後，執行 `python tools/lab.py state apply <file>`。工具先驗證整筆交易，再儲存重做日誌、替換狀態檔案，最後移除日誌。每個實驗室狀態指令都持有非阻塞式作業系統鎖；寫入程序若崩潰，鎖會自動釋放。復原程序會先重播已提交的日誌，再接受新工作。

## 階段

正常路徑為 onboarding → planning → preparing → practicing → reviewing → planning。允許停留在同一階段。暫停紀錄保留原本的 `resume_phase` 與非空原因；恢復時清除兩者。準備驗證失敗會記錄 blocked 與原因，並保留 preparing 恢復位置。受阻工作可回到 preparing 或 planning。

Preparing/practicing/reviewing 需要練習識別碼與修訂版。Practicing/reviewing 另外需要由持久驗證證據支持的有效就緒標記。學習者測試失敗時維持 practicing。已記錄的練習缺陷可搭配審查，讓 practicing/reviewing 回到 preparing；新契約需要新修訂版。

`check` 會獨立於教師結論保存報告。對目前修訂版執行預設檢查，會更新 `last_report_id` 並遞增狀態版本，但不改變階段。診斷用 `--preset` 執行不會更新它。

## 完成與觀察

完成練習時，結束審查，從 practicing 或 reviewing 進入 planning，並將 `{ "id": "exercise-id", "revision": 1, "report_id": "run-…" }` 附加至 `completed_exercises`。報告識別碼必須等於前一個工作階段最後一份符合資格的報告。須包含同修訂版的審查、學習者說明及持久參照。完成條件包括前一個工作階段成功的預設學習者檢查、未變動的學習者檔案，以及有效的就緒契約。既有完成歷史不能移除。CI 重新執行已記錄的原始碼與測試快照，因此後來的現行修訂版不會抹除或錯誤呈現已完成版本。

證據項目包含識別碼、時間戳記、練習識別碼與修訂版、技能、觀察、參照、提示程度（0–5）、教師解讀、low/medium/high 信心程度，以及可為 null 的 `supersedes`。自述保留在個人資料中。參照必須是 `evidence/`、`learner/artifacts/` 或 `learner/reviews/` 下的既有檔案；`reports/` 中的報告與現行練習原始碼不算持久參照。

提交引用原始說明的交易前，先儲存原始說明。執行的 `source_hash` 涵蓋實際執行的原始碼快照，包括額外測試。`student_source_hash` 涵蓋學習者原始練習目錄樹，避免新增驗收測試扭曲原始碼是否仍為最新的判斷。報告本身絕不是理解程度的證據。

`status` 檢查參照是否存在及發布完整性。缺少佐證時會回報，不會默默將孤立觀察視為有佐證。所有被引用的證據都應保留在磁碟上。執行快照預設被忽略，以便清楚顯示學習者變更；只透過 Git 備份時，須用 `git add -f` 明確封存被引用的報告及其子快照。絕不將刪除證據當作例行清理。

## 簡短指令（優先使用）

每個經路由的教學步驟執行一次 `./lab context --json`。尤其在學習者作答後，完成或審查請求會開始新步驟，即使指派前已讀取 context，也需要重新取得。這能先發現學習者在聊天之外執行的 `./lab check`，再決定是否需要再次檢查。Context 整合個人資料與工作階段、目前規格及有長度上限的可編輯原始碼、兩筆近期觀察、精簡報告組態，以及原始碼與契約是否仍為最新。`check_reusable` 表示成功的必要組態學習者檢查符合目前原始碼與契約，且沒有完整性錯誤。它不代表理解。Context 不會執行編譯器。

使用回傳的版本；成功的變更會回傳新版本。「一次」指該路由步驟一次，不是整段對話一次。只有中間有學習者指令、衝突、後續完成或審查步驟，或其他有實際需要更新資訊的情況，才再次讀取。

```sh
./lab prepare ID --assign --expected-version N
./lab session reviewing --expected-version N --next-action 'Await an explanation.'
./lab session paused --expected-version N --reason 'Time limit' --next-action 'Resume the saved review.'
./lab session resume --expected-version N --next-action 'Continue the saved review.'
./lab finish /tmp/completion.json
```

`prepare --assign` 需要已編寫的資產及通過的語意審查。它從 planning 進入 preparing、執行既有發布門檻，只有成功後才進入 practicing。失敗時保留 preparing/blocked 的恢復位置。

完成資料包為 `{ "schema_version": 1, "expected_version": N, "review": REVIEW, "evidence": [OBSERVATION] }`，使用 `review.schema.json` 與 `evidence.schema.json`。先將原始回答儲存在 learner/artifacts 並建立參照。審查包含英文說明摘要與具體下一步行動。`finish` 建立工作階段替換內容，並以原子方式提交全部紀錄；它要求非空證據陣列、相符修訂版、持久答案參照、仍為最新的預設通過結果、有效就緒標記，以及未變動的原始碼與契約。已有說明時，可直接從 practicing 完成；適用的完成門檻與離開 reviewing 時相同。版本只遞增一次。舊有 `state apply` 仍可使用，包括個人資料變更與缺陷紀錄。

框架變更可能讓歷史任務的現行就緒標記過期。保留完成紀錄及其快照；不要重新發布舊修訂版來掩飾變更。下一個新練習會以新框架驗證。完整 `ci` 仍需要有效的現行就緒契約；它不是例行恢復教學的指令。
