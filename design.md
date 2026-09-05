# 互動式 C++ 演算法與系統設計學習 Repo

日期：2026-09-05  
狀態：初步設計，可作為 Codex 實作依據。以下區分核心需求、第一版建議與待實測假設；不是已完成或已驗證的產品規格。

## 1. 目標與產品定位

建立一個直接以 Codex CLI 開啟的教學 repo。使用者輸入「開始」或「繼續」，agent 即透過訪談、短練習與實作證據理解使用者，再逐題安排練習與回饋。

動機是：長期使用 coding agent 後，使用者希望恢復親手實作、除錯與設計取捨的能力，同時利用強模型提供更個人化的教學。評估能力是調整教學的手段，不是考試或排名的最終目的。

核心要求：

- 使用者在本機編輯 C++，不建置 LeetCode 類型的 Web 介面。
- 新 repo 沒有預先填滿的題庫；包含教學規則、狀態格式、工具與一至兩種題目模板。框架驗證用 fixture 不視為正式課程。
- 語言以 C++20 為預設，個別題目可明確要求 C++23。
- 題目涵蓋演算法、資料結構、併發、系統元件與系統設計；以實際需求及限制驅動解法。
- 使用者負責練習區的實作。agent 負責教學與必要環境準備，不因測試失敗就自動代寫。
- 學習狀態存於 repo，可跨 CLI session 恢復；不依賴模型記得完整聊天。
- 驗收重點是：換一個情境、降低提示後，使用者能否獨立實作並解釋設計。

第一版不做：完整 LMS、多人帳號、排行榜、雲端執行平台、大量自主爬取專案、複雜多模型編排、全自動宣告使用者已精通某項能力。

### 1.1 Repo 語言規範

本文件可維持繁體中文，作為實作交接文件；最終 repo 以英文為主要語言，方便公開展示、外部貢獻與後續擴展。若將本文件納入公開 repo 的正式文件，應提供英文版本作為主要版本。

- Repo 內正式文件一律以英文撰寫，包括 README、AGENTS.md、teaching/ prompts、模板、題目敘述、設計筆記模板、素材說明、環境與貢獻指南。模型生成新題目時也必須遵守，不因當前對話為中文而生成中文版正式題目。
- 程式識別字、註解、測試名稱、CLI help 與錯誤訊息、schema 欄位及工具產生的正式報告使用英文；檔名與目錄名稱採英文。上游原始文件、授權文字及必要引用保留原文。
- 教學對話與臨時解釋依使用者偏好調整，可使用繁體中文；英文文件中的內容可在對話中用中文解說，不必另外維護整套中文文件。
- learner/profile.json 加入 preferred_interaction_language（例如 zh-TW）；repo 的正式文件語言固定為 en，兩者分開處理。使用者自己的自由文字、原始回答與逐字引用可保留原語言，供 teacher 追溯；系統整理的可重用摘要及正式紀錄使用英文。
- 第一版不建置多語系框架或翻譯流水線；將上述規則寫入 AGENTS.md 與生成流程，並納入題目及文件審查。

## 2. 核心架構與責任

| 層次 | 責任 | 不應承擔的工作 |
|---|---|---|
| 教學規則 | 訪談、選題、提示、診斷與回饋方式 | 以自然語言取代可執行的驗證 |
| 學習狀態 | 目標、先備能力、實作證據與當前進度 | 把自述或一次通過當作精通 |
| 題目與素材 | 需求、骨架、參考解、測試、來源與版本 | 未驗證就交給使用者 |
| 固定工具 | 建置、測試、狀態檢查、結果保存 | 自動推定使用者理解或直接改答案 |
| Codex teacher | 根據證據進行教學判斷 | 每輪重建所有工具與環境 |

設計原則：prompt 負責需要判斷的部分，腳本負責可重現的部分。第一版透過 Codex CLI 與本機指令工作，不要求額外 API key 或自建 agent framework。

## 3. 技術棧

| 項目 | 初步選擇 | 說明 |
|---|---|---|
| 語言 | C++20，按題開啟 C++23 | 使用 target 層級設定，不悄悄改變所有題目標準 |
| 編譯器 | Clang 主工具鏈，GCC 相容性檢查 | 實作時選擇並記錄確切版本與標準庫；不只固定編譯器名稱 |
| 建置 | CMake + Ninja | 每題獨立 target，預設只建置當前題目 |
| 設定 | CMakePresets.json | debug、release、asan、tsan；本機差異放 CMakeUserPresets.json |
| 測試 | Catch2 v3 + CTest | 單元、邊界與整合測試；CTest 管理執行、逾時及結果 |
| 動態檢查 | ASan + UBSan；TSan 獨立設定 | 僅執行適用的平台與題型；不把 sanitizer 無報錯當成完整正確性證明 |
| 開發支援 | clangd、clang-format，選用 clang-tidy | 產生 compile_commands.json；規則配合教學目標 |
| 流程控制 | Python + JSON Schema | CLI 使用 argparse 等標準庫；schema 驗證套件固定版本 |
| C++ 相依 | FetchContent，固定版本或 commit | 少量依賴先不導入完整套件管理器 |
| CI | GitHub Actions | 與本機使用相同指令；主要在 Linux 驗證 |
| 上游隔離 | 按素材提供獨立建置 adapter，必要時容器 | 完整上游專案保留自己的建置系統 |

第一版優先讓一般題目能在 Linux 與 macOS 本機使用；依賴 Linux 系統呼叫的題目必須標記平台需求。固定容器 image digest 可改善重現性，但不代表可消除 CPU 架構或 kernel 差異。

確切最低 CMake、Python、Clang/GCC 版本在實作時依選定環境確認，寫入環境文件；本設計不預先假定未驗證的版本組合。第一版不要求 C++ modules、額外 benchmark framework 或 property-testing framework。

## 4. 檔案架構

| 路徑 | 內容 |
|---|---|
| design.md | 本設計文件 |
| README.md | 安裝、開始、繼續、手動測試與復原方式 |
| AGENTS.md | 短入口規則、階段路由、學生檔案修改邊界 |
| teaching/interview.md | 初次訪談與短練習校準 |
| teaching/generate.md | 情境、規格、參考解、測試與挖空流程 |
| teaching/coach.md | 提示層級、避免代做、處理卡關 |
| teaching/review.md | 根據證據回饋與選擇下一步 |
| schemas/ | profile、evidence、session、exercise、material、report 的 JSON Schema |
| learner/profile.json | 目標、語言、偏好、可用時間、自述經驗 |
| learner/evidence.jsonl | 逐筆追加的能力觀察與來源 |
| learner/session.json | 當前題目、階段、待處理事項與恢復資訊 |
| learner/reviews/ | 每次練習的簡短回顧，按需讀取 |
| templates/implementation/ | 功能實作模板 |
| templates/debugging/ | 故障診斷與修復模板 |
| references/catalog.json | 候選與已驗證的上游素材索引，初始可為空 |
| references/materials/<material-id>/ | manifest、環境設定、adapter、來源與教學切入點 |
| exercises/<id>/README.md | 使用者可讀的情境、需求、限制與範例 |
| exercises/<id>/spec.json | 版本化題目契約與驗收條件 |
| exercises/<id>/src/、include/ | 使用者實作與提供的程式骨架 |
| exercises/<id>/tests/ | 公開測試與固定 seed 的測試產生器 |
| exercises/<id>/design.md | 設計假設、方案、估算與取捨，按題需要建立 |
| exercises/<id>/experiments/ | 負載或故障實驗，按題需要建立 |
| .instructor/<id>/ | 參考解、額外驗收測試、刻意錯誤版本與驗證證據 |
| tools/lab.py | 統一 CLI 入口 |
| tools/lab/ | schema、建置、測試、報告、狀態等模組 |
| tools/tests/ | 工具重要行為的測試與小型 fixture |
| cmake/ | 共用 target、編譯選項與 sanitizer 設定 |
| CMakeLists.txt、CMakePresets.json | 根建置入口與共用設定 |
| pyproject.toml | Python 需求與工具設定；相依採可重現的固定方式 |
| .github/workflows/ | 框架、素材與完成題目的 CI |
| build/、reports/、.cache/ | 可重建的產物、完整 log 與上游 checkout，不進 Git |

exercises/ 起初保持空白。不要為了示範而替使用者自動選定一整套課程。

.instructor/ 只是降低意外看見答案的機會，不是保密或安全邊界。生成與驗證階段可讀參考解；教學階段預設只讀規格、學生變更與測試證據，必要時才查教學資料，不主動洩漏解答。

學習狀態及題目可在私人 Git repo 保存；若將框架公開，排除個人紀錄與答案等不欲公開內容。上游程式的納入與散布要保留其授權及必要聲明。

## 5. 資料契約

所有結構化檔案帶 schema_version，寫入前驗證；狀態檔採原子替換。第一版假設單一 writer，遇到同時執行時應拒絕衝突寫入，而非覆蓋另一個 session。

| 資料 | 最少欄位 |
|---|---|
| profile | goals、language_standard、platform、time_budget、preferences、preferred_interaction_language、self_reported_experience |
| evidence | id、timestamp、exercise_id、exercise_revision、skill、observation、evidence_refs、hint_level、teacher_interpretation、confidence |
| session | phase、current_exercise_id、exercise_revision、last_report_id、pending_questions、next_action |
| exercise spec | id、revision、template、objectives、prerequisites、scenario、requirements、non_goals、cpp_standard、platform、editable_paths、provided_paths、acceptance_checks、seeds、resource_limits、material_ref |
| material manifest | id、source_url、commit、license、mode、toolchain、dependencies、prepare/check/reset adapter、resource_requirements、learning_targets、prerequisites、validation_status、validation_report |
| run report | id、timestamp、exercise_revision、source_hash、target_kind、toolchain、commands、exit_status、test_summary、seeds、failure_artifacts、duration、sanitizer、usage_if_available |

要求：

- 自述能力與實作證據分開；「知道 condition variable」不等於「能正確處理喚醒後條件仍不成立」。
- evidence_refs 指向相關程式版本、測試結果或使用者解釋，避免只存模型判語。
- confidence 是老師的暫時判斷，不是經過統計校準的分數。
- 原始觀察可追加更正與引用，不悄悄改寫歷史。
- 題目開始後，規格與測試不得因學生失敗而暗中放寬。若題目有錯，建立新 revision，說明修正並重新驗證。
- reports/ 可清除完整 log，但保留支撐能力判斷與題目發布的最小證據；清理時不能留下失效引用卻仍宣稱有證據。

## 6. 教學迴圈

### 6.1 開始與恢復

使用者輸入「開始」：讀 AGENTS.md；檢查環境與既有 session；有進度就恢復，沒有才訪談。訪談只問會影響下一題的資訊：想解決的工作問題、熟悉語言與領域、可用時間、近期卡點。

以一個短練習校準，避免先填長問卷。訪談結果先保存，讓使用者能更正誤解。

### 6.2 選題與準備

依目標、先備能力及近期證據，選一個主要學習目標。可選已驗證素材、模板變體，或生成自包含題目。新題目必須完成第 7 節的驗證才可交付。

### 6.3 實作與提示

交付題目後等待使用者實作，不在背景持續輪詢或改 code。使用者可自行執行 check，或請 agent 執行。

提示建議由淺入深：請使用者預測行為或描述思路 → 指出反例或失敗條件 → 提醒相關概念 → 局部偽碼 → 在使用者明確要求時提供完整解法。不是每次都必須逐級提問；依使用者指示與證據調整，避免把互動變成冗長審問。

教學模式預設不修改 editable_paths。環境或題目本身有錯時可修復提供的檔案，需說明對題目契約的影響；不得用「修復」名義代做學習目標。

### 6.4 回顧與下一題

測試通過後，請使用者解釋一個關鍵取捨，或預測需求改變後的行為。失敗時先分辨概念、API、實作、除錯方法、環境或題目缺陷。

| 觀察 | 下一步示例 |
|---|---|
| 概念理解不完整 | 降低周邊複雜度，聚焦一個反例 |
| 主要是 API 不熟 | 提供短參考，保留原本的概念挑戰 |
| 大量提示後完成 | 記錄為有協助完成，之後安排換情境重練 |
| 能獨立完成並解釋 | 加入新限制或相鄰概念 |
| 題目或測試有錯 | 修正題目，不把失敗算在學習者身上 |

保存簡短回顧、證據與 next_action；完整聊天不必每次重新載入。

### 6.5 狀態轉移

主流程：onboarding → planning → preparing → practicing → reviewing → planning。

任一階段可 paused，記錄恢復位置。preparing 驗證失敗進 blocked，不得轉 practicing；學生測試失敗仍留在 practicing，不等於框架故障。工具只能記錄測試結果，不能僅依 pass 自動宣告學會。

## 7. 題目生成與品質驗證

固定順序：定義情境與需求 → 寫可觀察的驗收條件 → 參考實作與測試 → 驗證完整版本 → 建立學生骨架 → 驗證挖空範圍 → 發布題目。

### 7.1 情境與挖空

情境限制必須真正影響解法。例如「記憶體受限、消費速度不穩定的事件服務」可引出 bounded queue、背壓與丟棄策略；不能只把陣列題換成公司故事。

挖空對應主要學習目標，提供無關的輸入解析、初始化與測試入口。第一版優先提供能編譯但尚未通過功能測試的骨架；若學習目標就是修復編譯錯誤，必須在 spec 明示。

### 7.2 測試策略

- 例子與邊界：空輸入、容量邊界、重複資料、錯誤輸入、需求指定的溢位行為。
- 隨機與性質：固定 seed，檢查不變量；可在小規模輸入上與簡單、獨立的 oracle 比對。保存失敗輸入，以便重現。
- 故障與併發：適用時加入錯誤路徑、逾時、TSan 與可控制的同步情境；避免只靠 sleep 猜執行順序。
- 刻意錯誤版本：依教學目標注入 off-by-one、錯誤邊界或錯誤同步等問題，確認測試能抓到。失敗應對應預期原因，不能把無關編譯失敗當成功抓錯。
- 效能：有明確限制才測；固定負載並記錄環境，不用脆弱的單次耗時作唯一判斷。

參考解與測試可能共享同一誤解，因此不能只檢查「參考解全過」。驗證報告需列出需求與檢查的對應、刻意錯誤版本結果，以及尚未覆蓋的限制；老師審查語意，工具提供執行證據。

題目進入 ready 的條件：spec 合法、參考版本通過、適用動態檢查完成、目標錯誤版本被偵測、學生骨架行為符合預期、提示與可編輯檔案明確。驗證綁定題目 revision 與來源 hash，修改後需失效並重驗。

## 8. 開源參考素材

reference list 應逐步成為經整理、可重現的素材庫。專案知名度或測試數量不直接代表某個子系統適合教學；選材還要評估邊界、測試品質、依賴與可教的取捨。

| 模式 | 做法 | 成本與注意事項 |
|---|---|---|
| 參考設計 | 讀取上游需求與取捨，生成自包含練習 | 環境最單純，但新實作與測試仍需完整驗證 |
| 擷取子系統 | 固定 commit，保留核心程式及適用測試，用替身隔離外部依賴 | 切割可能改變語意；替身不能移除原本要學的故障或併發行為 |
| 完整上游 | 在固定版本的完整 checkout 修 bug、補功能或做設計實驗 | 最接近工作，也有最高建置與閱讀成本 |

素材準備與教學執行分開。新素材先 candidate，完成來源、授權、工具鏈與基準測試確認後才 ready；無法重現則 blocked，保留原因。正式教學優先使用 ready 素材。

完整上游專案保留自己的建置工具與依賴版本，透過 prepare/check/reset adapter 呼叫。不要強迫全 repo 使用同一套第三方版本，也不要每輪重新下載上游。reset 只作用於該素材工作區，保留或備份學生修改，不執行會波及整個 repo 的破壞性清理。

歷史 bug fix 可作為進階素材：固定 bug 前後版本、補 regression test、確認前者能重現且後者修復。接受符合需求的其他解法，不以是否重現作者 patch 判分。

第一版僅建立素材契約與候選流程；不預先宣稱任何具體專案已驗證。先以少量人工挑選素材驗證價值，再開放自主引入。

## 9. 系統設計練習

採用「提出方案 → 加入負載或故障條件 → 修改設計 → 實作關鍵元件 → 檢視實驗」的流程。

design.md 記錄需求、容量假設、備選方案、選擇理由與已知限制；experiments/ 保存可重跑的負載或故障測試。自動化驗證可執行的承諾，老師評估假設與取捨，不能將單元測試通過等同整體設計良好。

例如 bounded queue 題目先完成容量與關閉語意，再加入生產速度大於消費速度的情境，要求選擇阻塞、拒絕或丟棄策略；後續是否練併發由證據決定，不一次塞入所有功能。此例只示意題型，不是預設課程。

## 10. CLI 與自動化契約

以下命令是建議介面，不代表目前已存在。

| 指令 | 行為 |
|---|---|
| python tools/lab.py doctor | 檢查工具鏈與平台，輸出缺少項目；不擅自升級系統工具 |
| python tools/lab.py init | 初始化空學習狀態與目錄，不生成正式題目；可重複執行且不覆寫進度 |
| python tools/lab.py prepare <id> | 根據已存在的 spec 套模板、準備環境、執行題目驗證並保存報告 |
| python tools/lab.py check <id> | 只建置當前學生版本，執行適用測試與檢查，不修改學生實作 |
| python tools/lab.py status | 顯示當前題目、階段、最後結果與待辦；不呼叫模型 |

生成 spec、參考解與教學內容由 Codex 完成；prepare 是確定性工具，不暗中接 API 生成缺少檔案。缺檔就回傳可操作的錯誤。

支援人類可讀摘要與 --json 輸出。退出碼需區分成功、學生測試失敗、環境或配置錯誤，並在 README 記錄。每次執行保留完整 log 路徑、seed、版本、時間與精簡結果。

CI 分三類：工具/schema 的重要行為、題目參考版本與素材驗證、已宣告完成的學生實作。當前尚未完成題目的預期失敗不阻擋整個 repo。生成中的題目可進私人版本控制，但未通過驗證不得標為 ready。

工具測試聚焦狀態恢復、避免覆寫、版本失效、退出碼與驗證閘門；不需要為每個低風險包裝函式寫鏡像測試。

## 11. 模型分工與成本

第一版採「最強可用 teacher + 固定腳本」。保留未來 worker 介面，但先不做自動多模型調度；額外模型交接、重複上下文與返工可能抵銷節省。

| 執行者 | 工作 |
|---|---|
| 腳本 | 建目錄、套模板、建置、測試、擷取 diff、驗證 JSON、保存結果 |
| 便宜模型，後續選配 | 素材分類、依明確規格產生例行骨架、帶原始引用的紀錄整理 |
| 強模型 | 訪談、學習目標、題目與測試語意審查、誤解診斷、提示、設計取捨 |

便宜模型不得獨自更新「已學會」結論；摘要帶證據來源。不假定在 prompt 寫模型名稱就能切換執行模型，實際分流須由所用 CLI 的已支援設定或後續控制程式完成。API 模式應明確選配，不能默默把 Plus 使用者切到另行計費的 API。

### 11.1 用量估計與控制

示意：6 次模型回合，每次平均 8k 輸入與 1k 輸出，累計約 48k 輸入 + 6k 輸出。這不是實測；未計額外工具回合、推理用量與快取差異，不能直接換算成 Plus 可完成幾題。每次讀 40k 上下文則同樣六回合已有 240k 輸入。

高成本來源：首次引入上游、題目生成反覆修復、重讀大型檔案與歷史、把完整成功 log 送回模型、無止境重試。

優化順序：

1. 本機測試與使用者實作期間不呼叫模型，不背景輪詢。
2. AGENTS.md 保持短小；按階段載入規則，只讀相關能力證據、當前 spec 和 diff。
3. 完整 log 保存在檔案，預設回傳摘要，需要時再讀細節。
4. 重用驗證過的模板、素材、測資與參考解，變更 revision 才重驗相關部分。
5. 生成修復採有限次重試；建議初始上限兩次自動修復，仍失敗則 blocked 或換 ready 素材。這是可調初始值。
6. 按階段量測，再把可可靠驗收的例行工作交給便宜模型。

usage_if_available 記錄模型、階段、可取得的輸入/輸出/快取/推理 token、工具回合、重試與耗時；拿不到的欄位寫 null，不推測填值。不要把可見文字長度冒充完整 token 消耗。

### 11.2 Plus 試行節奏

初始建議每週三次、每次 45–60 分鐘，當中約 25–40 分鐘自己實作；強模型集中在開場、卡關與收尾，約三至六次互動。這是安排假設，不是配額保證，也不是必須限制提問次數的教學規則。

工作使用與練習可能競爭同一用量；使用者可從 Codex /status 與帳號用量頁觀察。訂閱額度與模型支援會變，不能硬編碼在 repo。API 另行計費；本設計不預設有 API 預算。

先累積約十次練習，再檢查各階段耗用、返工率與無提示重做表現；優化目標是有效學習成本，不只是最低 token。不在第一版內建排程或自動購買額度。

## 12. 第一版實作順序與驗收

| 階段 | 交付 | 驗收 |
|---|---|---|
| 1. 可執行骨架 | 目錄、schemas、CMake presets、Catch2、doctor/init/status | 乾淨環境可初始化；不覆寫狀態；無正式題目也能使用 |
| 2. 題目驗證 | 兩種模板、prepare/check、報告與版本綁定 | 參考解通過、目標錯誤被抓、未驗證題不能開始；check 不改學生 code |
| 3. 教學閉環 | 訪談、教學與回顧 prompt、狀態恢復 | 「開始」能完成一輪；新 session 可接續；提示使用有紀錄 |
| 4. 素材試接 | manifest、catalog、一份挑選後的素材 | 固定 commit 能重現；來源、授權、依賴及限制明確 |
| 5. 成本校準 | 分階段用量記錄、十次練習回顧 | 能找出高成本階段，再決定是否需要便宜 worker |

先跑通單題，不先生成完整課程。完整上游 adapter、多模型路由、大型素材庫可延後；系統設計先以設計文件加一個可執行元件落地。

最小端到端驗收情境：初始化 → 短訪談 → 生成並驗證一題 → 學生實作失敗 → 提示 → 再測 → 設計解釋 → 保存證據 → 重新啟動 CLI → 正確恢復下一步。另驗證題目自身出錯時不會降低學習者能力判斷。

## 13. 主要風險與待決事項

| 問題 | 目前處理方向 | 待驗證 |
|---|---|---|
| 解答與測試共享誤解 | 需求對應、簡單 oracle、目標錯誤版本與語意審查 | 能否抓到真正相關的錯誤 |
| 老師過度代做 | 明確編輯邊界、分層提示、記錄協助程度 | 使用者是否恢復獨立能力 |
| 進度紀錄失真 | 自述/證據分開、來源可追溯、允許更正 | 摘要是否足以跨 session 教學 |
| 上游依賴成本失控 | 固定版本、adapter、候選/ready 分離 | 哪些素材適合擷取或完整引入 |
| 併發測試不穩定 | 控制同步、逾時、適用 sanitizer、保留重現條件 | 平台差異與未涵蓋排程 |
| Plus 耗用過高 | 重用素材、縮小上下文、限制生成返工 | 十次實測後的可持續頻率 |

實作前仍須選定：確切工具鏈版本、第一個短校準題方向、第一份上游素材、模型選配能力，以及是否需要 Windows 支援。這些不應阻擋完成單語言、單使用者、自包含題目的第一個閉環。

## 14. 參考文件與時效

以下是討論中查閱的官方文件，提供實作時查核；本文件的架構與數值示例是設計建議，不是工具提供商的保證。

- [CMake Presets](https://cmake.org/cmake/help/latest/manual/cmake-presets.7.html)
- [Catch2 CMake integration](https://catch2-temp.readthedocs.io/en/latest/cmake-integration.html)
- [Clang AddressSanitizer](https://clang.llvm.org/docs/AddressSanitizer.html)
- [Clang ThreadSanitizer](https://clang.llvm.org/docs/ThreadSanitizer.html)
- [OpenAI Codex / Work pricing and usage](https://learn.chatgpt.com/docs/pricing)

模型名稱、方案額度及工具版本以開始實作和實際使用時的官方資訊為準。設計本身應避免依賴特定一代模型或固定訊息配額。
