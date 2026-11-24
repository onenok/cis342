## 2026-11-24 — 新增 `[INT-04]` 現場上傳測試入口（不用 Gradio）

**摘要**：教授現場會給幾張測試圖，需要「上傳 → 辨識 → 看結果」。原本 §10 的
`try_plate()` 在 Colab 其實已經會跳上傳框，但它綁在「選資料夾 → 選編號」的流程裡，
一次多張不好用、也不好現場操作。所以新增兩格，只做一件事：

- `[INT-04]` 定義 `present_test(paths=None, upload=None, save_dir=None, figures=True)`
- 最後一格是執行入口，預設 `RUN_LIVE_TEST = False`

**為什麼不用 Gradio**：Gradio 要額外安裝、另開連線埠，Colab 上常因版本衝突爆掉，
而需求只是「上傳檔案」。Colab 內建 `google.colab.files.upload()` 就夠，
且失敗時自動退回「貼上路徑」模式，不會整格紅掉。

**行為**

| 情況 | 走法 |
|---|---|
| Colab，`paths=None` | `files.upload()` 跳上傳框，可一次選多張，落地 `/content/uploads/` |
| 上傳不可用（本機／無 colab 模組） | 退回 `input()` 貼路徑，多張用逗號分隔 |
| 指定 `paths=[...]` | 直接跑，不互動（給程式呼叫） |
| 多張 | 逐張印一行，最後再印一張彙總表（檔名／預測／格式合法／信心／路徑） |
| 單張 | 只印一行，不印表 |
| 找不到檔／辨識出錯 | 印訊息後跳過，不中斷整批 |

**刻意做成「預設不執行」**：`RUN_LIVE_TEST = False`。原因是 Run All 時若直接呼叫
`files.upload()`，Colab 會停在等待上傳而讓整份 notebook 卡住 —— 交付版要能一鍵跑完。
現場要用時改 `True`，或在新的臨時格直接寫 `present_test()`。

**實測**（`.venv` + 兩張 `data/images` 整車照）

- 兩張都跑完、印出表格、`valid=True`，無例外
- 單張：`XU5 / fallback-wholeimage`，只印一行
- 非互動環境 `input()` → 捕捉 `EOFError`，回傳 `[]`，不崩潰
- 不存在的路徑 → 印「找不到檔案」後回傳 `[]`
- 執行入口在 `RUN_LIVE_TEST = False` 時確認不會觸發上傳

**同步**：`notebooks/lpr_dev.ipynb` 與 `colab_manually_sync/…ipynb` 都追加同樣兩格
（現在各 72 格）；交付版的 21 個既有輸出格未受影響。兩份都補了 cell `id`
（原本 append 時缺 id，nbformat 會警告）。

---

## 2026-11-23 — 合 PR #8（78 張口徑），修兩處文字，重畫第 8 頁圖表

**摘要**：隊友把整條 B 線換成 78 張口徑（PR #8，`ca8e6de`），並用我給的 17 個 stem 自驗通過。
合併後我補了三件他沒做或做不完整的事。

**核對結果（用 `debug/_stage_eval.csv` 逐張重算）**

| 項目 | 他寫的 | 我核 | 結果 |
|---|---|---|---|
| 78 張、exact 38、錯 40 | 同 | 同 | ✅ |
| 四類 29 / 4 / 6 / 1 | 同 | 同 | ✅ |
| IoU<0.5 26 張 11.5%／≥0.5 52 張 67.3% | 同 | 同 | ✅ |
| path 分佈 detect 31／selfsplit 26／selfsplit+fallback 16／detect+fallback 5 | 同 | 同 | ✅ |
| 融合 CER 0.385 | 同 | 0.3848 | ✅ |
| 單路 CER 0.478 | 同 | 0.4827（macro）／0.4868（micro） | ⚠️ 差 0.005 |

**我改的三件**

1. **「all five one-glyph」→「all four」**：他把「差 1 字元」改成 4 張，但下一條 bullet 仍寫 five。
   逐張驗過那 4 張（`MZ9073→MZ9078`、`VC6296→VG6296`、`WP7702→HP7702`、`EZRA→ELRA`）
   全部 `postprocess()` 回 `valid=True` 且 `fixed == pred`，所以論點成立，只是數字要跟著改。
2. **重畫 `slides/assets/a-ceiling.png`**：他只改了第 8 頁的文字（11.5%／67.3%），
   **圖還是舊的 95 張分層**（8.3%、n=36/19/26/14、overall 40.0%），同一頁自相矛盾。
   `debug/make_a_ceiling.py` 讀的是 `debug/ceiling.csv`（95 列），所以我另寫
   `debug/make_a_ceiling78.py`，從 `_stage_eval.csv` + `prep_ious.csv` 重建
   `debug/ceiling78.csv` 再出圖：11.5% (n=26)／58.8% (n=17)／72.7% (n=22)／69.2% (n=13)，overall 48.7%。
3. **中文版全線對齊 78 張**：第 8、11、14、15 頁與 Q&A 備註。中文版原本還停在 95／40.0%／57 張錯。

**交付版 notebook**：把 §9 整格從 `lpr_dev` 覆蓋過去（PR #8 只改 `lpr_dev`），
兩份 code+markdown sha256 現在相同（`4cdbce81`），交付版 21 個輸出格保留，不需重跑。

**單路 CER 的 0.478 vs 0.483**：不是 GT 正規化問題（我用的是清洗後的 GT）。
融合 CER 兩邊都是 0.385，只有單路不同 → 差異在「單路那條字串取哪一個」。
CER 不在任何一頁投影片上（原本只在英文 Q&A 備註，PR #8 已拿掉），
所以採用他表格自己的 0.478，不把我的 0.483 混進去。

---

**摘要**：隊友按 #42 的建議把錯誤分佈改成四類互斥（45 + 5 + 6 + 1 = 57），
圖與 bullet 都重畫，PR #6（`156fcd7`）與 PR #7（`710b797`）已推。
我核對後合併，並補了三件他沒做或沒做對的事。

**核對結果**

| 項目 | 結果 |
|---|---|
| `40.0% / 69.2%`、`+7.4`、`45 of 57` | ✅ |
| 那五組字元對 `1-6 / 3-8 / C-G / W-H / Z-L` | ✅ 與 `debug/_stage_eval.csv` 一致 |
| 四類互斥相加 = 57 | ✅ 圖與表都對 |
| `the other 12 are same-length confusion` | ❌ 5 + 6 = 11，第 12 張是 `DM6368→DMA6368`（多一個字元） |

**我改的三件**

1. **第 15 頁 bullet**：改成「11 張長度不變 + 1 張多一個字元」，讓 45 + 11 + 1 = 57 讀得通。
2. **交付版 §9 同步**：PR #7 只改 `notebooks/lpr_dev.ipynb`，`colab_manually_sync/` 那份
   仍是 `41.1%`（3 處）、「56 張錯誤」、易混 10 張。教授點開的連結是交付版，所以必須同步。
   已把 §9 的 markdown cell 整格覆蓋，兩份 notebook 的 code+markdown sha256 現在相同
   （`3d50cd88`），交付版 21 個輸出格完整保留，不需重跑。
3. **中文版三處**：第 11 頁 `41.1% → 40.0%`、第 14 頁 `+8.5 → +7.4`、
   第 15 頁改成與英文版同一組數字與敘事。

**口徑澄清（回應 #43）**：我在 #42 說「57 張錯誤裡有 39 張 pred 本來就合法」是錯的。
那 39 是 `debug/ceiling.csv` 的 `valid` 欄，語意是「`read_plate()` 最後選中的候選是否合法」，
不是對最終 pred 字串重跑 `postprocess()`。用現行程式重跑同樣 57 個 pred 得到
**valid=True 27 張**，與隊友獨立算出的 27 完全一致。已寫入 mistake-log。

---

## 2026-11-23 — 檢查 Colab 執行結果，發現 `shared/stages/` 混到舊版 A 線的殘留檔

**摘要**：使用者在 Colab 上跑完交付版並下載回來（21 個 cell 帶輸出、6 張圖、0 error）。
我逐項核對每個印出來的數字，發現一個跨章節的問題：
**簡報 §9 的「95 張」不是現行 A 線的產物**，其中 17 張是 11-22 的舊檔。

**Colab 全新環境實跑（與簡報對照）**

| 項目 | Colab 輸出 | 簡報 | 結果 |
|---|---|---|---|
| LOC recall@1 / recall@k | 51.5% / 60.6%（99 張，平均最佳 IoU 0.503） | 同 | ✅ |
| 過 0.60 門檻 | 78 / 99 = 78.8% | 同 | ✅ |
| GEO 校正 / 回退 | 84 / 16，傾角 12.1° → 0.0° | 同 | ✅ |
| SEG 遮罩小於整張矩形 | 100 / 100 | 同 | ✅ |
| POST-01 | 14 / 14 | 同 | ✅ |
| EV-01（26 組） | 69.2% / CER 0.158 / valid 88.5% | 同 | ✅ |
| `[OCR-02]` self test | 12/30 = 40.0% | （不在簡報上） | 與本機 36.7% 不同 |

**問題：`shared/stages/` 只增不減**

`export_dataset_frontend()` 只會寫入「這一批通過門檻」的圖，**不會刪掉上一版留在目錄裡的**。
`b65d5f8`（11-22 14:12）把顏色遮罩改成 `plate_color_masks_ladder()`（V=170 + V=220），
候選分數因此改變，通過 0.60 門檻的張數由 95 降到 78，但那 17 張舊圖仍留在目錄裡。

我用現行程式對那 17 張重跑 `localize()`：

```
top-1 分數 0.457 ~ 0.597，17 / 17 全部低於 LOC_ACCEPT_SCORE = 0.60
```

**對 B 線的實際影響**（`debug/_stage_eval.py`，逐張重跑 `read_plate()` 與單路徑 `recognize()`）

| 集合 | n | 兩路融合 | CER | 只用自研切字窗 | CER | 融合增益 |
|---|---|---|---|---|---|---|
| 全部（= 簡報的 95 張） | 95 | 38（40.0%） | 0.482 | 31（32.6%） | 0.574 | +7.4 點 |
| 其中 11-22 舊檔 | 17 | **0（0.0%）** | 0.929 | 0（0.0%） | 0.990 | +0.0 點 |
| 其中 11-23 現行 A 線 | 78 | **38（48.7%）** | 0.385 | 31（39.7%） | 0.483 | +9.0 點 |

也就是說：簡報上的「95 張 / 40.0% / +7.4」在該集合上是**算得對的**，
但那個集合 = 78 張現行 A 線 + 17 張已不可能再產生的舊圖，而 17 張一張都沒讀對。
現行程式的真實表現是 **78 張 / 48.7%**。

**為什麼這次不改簡報數字**：§9 的錯誤分佈（57 張錯、漏字 45 張）也是用這 95 張算的，
換分母要連同第 11、14、15 頁與兩張圖一起重做，上台前 12 小時做這件事的風險
高於它帶來的收益。改為在 Q&A 準備答案：若被問「為什麼 78.8% 過門檻卻有 95 張」，
回答「95 張含早期版本的產物，現行門檻只產 78 張，那 78 張的融合準確率是 48.7%」。

**待辦（上台後）**：清掉 `shared/stages/` 的 17 個殘留檔，並在 `[INT-01]`
的全量匯出前刪除同批 stem 的舊階段檔，避免同樣的污染再發生。

---

## 2026-11-23 — `[OCR-02]` self test 改成多輪抽樣，並顯示平均

**摘要**：原本的 `[OCR-02]` self test 只抽 6 張，在 40% 左右的準確率下很容易抽到 0/6，
在台上或報告裡會嚴重低估方法的好壞。改成 **5 輪 × 6 張**，每一輪的每一張都印出來，
最後把各輪平均放大顯示。

**先修正一個事實**：這個 self test 原本**不是隨機抽樣**，而是
`[s for s in sorted_stems if s in _gt][:6]` —— 依檔名排序取前 6 張，是確定性的。
我上一輪對使用者描述成「隨機抽 6 張」是錯的，已記入 mistake-log。

**新的行為**

| 項目 | 值 | 說明 |
|---|---|---|
| `_OCR_ROUNDS` | 5 | 抽幾輪 |
| `_OCR_PER_ROUND` | 6 | 每輪抽幾張 |
| `_OCR_SEED` | 342 | `random.Random(342)`，固定種子 |

- **固定種子**是刻意的：報告要能重現，重跑整份 notebook 必須得到同一批樣本與同一個平均。
  換樣本只要改 `_OCR_SEED`。
- **辨識結果有快取** `_ocr_cache`：5 輪共 30 次抽樣只涵蓋 28 張不同影像，
  沒有快取就會對同一張圖重跑 OCR。
- **逐張輸出保留**，每輪尾印 `→ hits/n = x%`。
- **最後的總結用 `IPython.display.HTML` 放大**（44px、綠色 `#2A9D8F`），
  因為平均值夾在 30 行逐張輸出裡一定會被忽略。IPython 不可用時退回
  `===== [OCR-02] 平均字串完全正確率 = x% =====` 的純文字。
- **同時報 macro 與 micro**：headline 是「各輪準確率平均」（使用者要的），
  下面再附「合計 hit/total」，因為兩者可能不同，只給一個會誤導。

**實測結果**（`.venv` 重跑，0 error）
```
各輪準確率：50.0% / 16.7% / 50.0% / 16.7% / 50.0%
合計 11/30 = 36.7%（28 張不同影像，已快取）
```
單輪從 16.7% 到 50.0% 跳動，正好證明原本「抽一次 6 張就下結論」的做法不可靠。

**⚠️ 上面那組數字已被證明是本地環境污染，不是乾淨結果。**
2026-11-23 22:20 在 Colab 全新環境重跑，同樣的 `_OCR_SEED=342` 得到
`50.0% / 33.3% / 50.0% / 33.3% / 33.3%`，合計 **12/30 = 40.0%**，不是 36.7%。

原因是抽樣池 = `shared/stages/` 的 stem 數：
- 本機有 **95** 個 stem，其中 17 個是 11-22 的舊檔（見下一節）
- Colab 從空目錄開始，`[INT-01]` 全量重跑後只有 **78** 個 stem

固定種子只固定「從池子裡抽哪幾個索引」，不固定池子本身。所以這個 self test
的數字**不可跨機器比較**；要當成正式數字引用時，必須先確認 `shared/stages/`
的 stem 數，或改用 `[EV-01]` 的 N=26 評估。

**未改動**：`[EV-01]` 的 N=26 評估仍是正式數字來源；這個 self test 只驗證
「`[OCR-02]` 的函式接線正確」，兩者的分母與抽樣方式都不同，註解已寫明
「這是定位已命中的子集，不代表全 pipeline 準確率」。

---
## 2026-11-23 — 交付版 notebook 全量重跑驗證，並修掉一句過時的 AI 聲明

**摘要**：`colab_manually_sync/CIS342_Group6_Project_LPR.ipynb` 與 `notebooks/lpr_dev.ipynb`
的 code cell 逐字相同（sha256 `2302ce9a`），`93fe0da` 之後沒有任何未提交改動，所以
「有沒有修好」這個問題的答案是**已經修好並已推送**。本次另把它整份重跑一次確認沒有退化。

**重跑方式**：`.venv` 內 `jupyter nbconvert --execute`，輸出到 `%TEMP%` 而不覆蓋版控檔案，
避免把執行輸出寫進 repo。結果 **41 個 code cell、0 個 error**。

關鍵數字與簡報一致（用來確認不是空跑的假數字）：

| 檢查點 | 輸出 |
|---|---|
| `[LOC-02]` self test | recall@1 **51.5%**、recall@k **60.6%**、平均最佳 IoU **0.503** |
| `[GEO-01]` self test | 有校正的 84 張：平均傾角 **12.1° → 0.0°** |
| `[EV-01]` self test | N=**26**、整牌正確 **69.2%**、CER **0.158**、格式合法 **88.5%** |
| `[POST-01]` self test | `POST_PASS` **14/14** |

有兩個 self test 在這種環境下是預期略過的，不是壞掉：`[S0-5]` 印「本機環境，跳過 Colab
就緒檢查」；`[INT-03]` 印「找不到 test demo 資料夾，略過」——後者是刻意設計成沒有
`test demo/` 也能跑完整份 notebook。

**修掉的問題**：cell 2「我未使用 AI 的部分」第 4 條寫
「各階段演算法選型與調參：…（**目前僅有 `TODO` 佔位實作**）」。
這句在骨架階段是對的，但 `[LOC-01]`／`[LOC-02]`／`[SEG-01]`／`[GEO-01]` 早已實作完成，
留著會讓 AI 聲明自相矛盾——同一份文件上方表格承認 AI 產出了這些實作，下方又說它們只是
`TODO` 佔位。改為「（AI 已產出可端到端運行的初版，本人尚需逐段檢視、調參與驗證）」，
既保留「這件事該由本人負責」的原意，也不再與事實衝突。

改動只動這一行，兩份 notebook 同步修改，改後 code 內容 hash 仍相同。

---
## 2026-11-23 — 中文對照版簡報（`slides/main.zh.md` + `slides/assets/zh/`，**非上台用**）

**摘要**：新增一份 15 頁繁體中文簡報，內容與 `main.md` 逐頁對應，用途是讓作者本人
先讀懂自己那半邊在講什麼，再決定台上怎麼講。**上台仍然用英文版 `main.md`**，
兩份檔案互不引用，改一邊不會動到另一邊。

**為什麼要另生成圖表，而不是叫 matplotlib 換字型就好**：中文標籤的視覺寬度與英文不同
（例如「定位 IoU 區間」比 `localisation IoU band` 短很多），直接沿用英文版的
`figsize` 會讓長條圖留白過多、或 `a-geo.png` 的頂部標題被裁掉。所以
`debug/make_a_zh.py` 是一份獨立腳本，六個 `fig_*()` 各自控制版面，
**選圖、數值、圖片尺寸與英文版完全一致，只換標籤文字**，確保兩份簡報講的是同一批數字。

**為什麼 B 線五頁沿用英文原圖**：`b-errors.png`、`b-ocr-pipeline.png`、
`b-results-scope.png` 的產生腳本在隊友手上（見 `shared/` 與 bridge #37），
重畫等於我這邊自己生一份沒有權威性的圖，日後他改圖兩邊就會不一致。
因此在中文版這幾頁下方加一行註記「隊友產生的英文原圖」，讀者不會誤以為是翻譯漏做。

**B 線的數字差異**：英文版第 15 頁寫「45 of **56** wrong plates」「of **69** images at
IoU < 0.5, only **2.9%** read correctly」。實算是 95 張中 wrong 有 **57** 張、
IoU < 0.5 是 **36** 張（讀對 3 張 = **8.3%**），而 **69** 是「不在 `rectified_auto`
的張數」（95 − 26），那批讀對 20/69 = 29.0%。三個數字混在同一個句子裡。
已在 bridge #37 把核算過程寄給隊友確認；**英文版未改動**（那是他的頁面），
中文版先按實算數字寫，並在講者備註用 `※` 標明待同步。

**排版修正**：中文版字級 24px / line-height 1.4，比英文版吃高度。
實測不溢出的寬度上限：dataset `880`、loc-candidates `790`、recall `960`、
seg-mask `950`、geo `880`、ceiling `540`、b-results-scope `510`、b-errors `620`。
其中 ceiling 與 b-results-scope 兩頁原本沿用英文版的 `620` / `690`，
最後一條 bullet 會壓到 footer，縮圖並砍短 bullet 後才通過。

**驗證**：`npx @marp-team/marp-cli main.zh.md --allow-local-files --images png`
渲染 15 張，逐張目視確認無溢出、footer 與頁碼未被遮蓋。

---
## 2026-11-23 — 補完 A 線 Marp 簡報六頁（`slides/main.md` 第 3–8 頁 + 6 張實跑插圖）

**摘要**：`project/slides/main.md` 從 8 頁長到 **14 頁**（封面 1 + A 線分隔 1 + A 線 6 + 共用契約 1 + B 線 5）。所有數字都是**重跑
notebook 函式量出來的**，沒有一項沿用舊稿。

**為什麼要做**：使用者與隊友 11-24 13:00 要上台，隊友的 agent 已完成 B 線，
A 線只有一個 `TODO(nok)` placeholder。這批必須在今晚完成。

**A 線六頁與各自的唯一論點**

| 頁 | 標題 | 論點 |
|---|---|---|
| 3 | 100 plates, no plate strings in the source | 資料集只有框、沒有字串，文字是手打的 |
| 4 | Localisation is a proposal step, not a detector | `localize()` 回前 5 個候選，不是單一答案 |
| 5 | Where the locator stands | recall@1 51.5% / recall@5 60.6%，分佈是雙峰 |
| 6 | Extraction answers "which pixels", not "where" | `segment()` 的真正輸出是 mask，不是裁切圖 |
| 7 | Rectification: fit four edges, not one rotated box | `minAreaRect` 無法表達梯形，所以逐邊擬合 |
| 8 | The ceiling is localisation, not recognition | IoU<0.5 只有 8.3%，OCR 再好也救不回來 |

**為什麼是 6 頁而不是原本說的 5 頁**：使用者在表單中同意「5 頁 + 一頁未來方向」，
所以第 8 頁（`The ceiling is localisation`）同時是「發現」與「下一步」，
不另開一頁講 YOLO/CNN，避免與 12/18 的最終版承諾綁死。

**為什麼重測而不是抄舊稿**：舊稿散落在 markdown 與先前的口頭討論裡，彼此不一致
（例如定位 recall 曾寫 49.0%、59.0%、0.487，與 notebook 的 51.5%、60.6%、0.504 不符）。
原因是我第一次自寫腳本漏了 `preprocess()` 與 `[D1-03]` 的 `_parse_bbox`。
改用 notebook self test 的同一條路徑後數字才對上，於是全部重算並存成
`debug/prep_ious.csv`（99 列）與 `debug/ceiling.csv`（95 列）。

**圖片素材的兩個陷阱（已修）**

1. `shared/stages/<stem>_05_rectify_mask.png` 是**校正後** 480×140 的遮罩，
   不是擷取階段的遮罩。要畫 SEG 那頁必須現場呼叫 `segment(img, quad)`，
   否則會拿錯階段的圖去示範「擷取」。
2. `_gt_quad_from_label()` 回傳的是原圖座標，沒有乘上 `MAX_SIDE` 的縮放；
   與 `localize()` 的輸出比 IoU 前必須自己乘 `min(1, MAX_SIDE/max(h, w))`。
   另外 `localize()` 的 `_iou_quad` 是**軸對齊外包框** IoU，不是多邊形 IoU。

**排版修正（渲染驗證後才發現）**

- `marp-cli` **必須加 `--allow-local-files`**，否則所有本地圖片靜默變成空白。
- `Marp` 的 `section` 是 grid 容器，垂直置中靠 `align-content: center`，
  `justify-content` 改不動它。已在 `style:` 段加 `align-content: start`
  讓所有內容頁齊頂，`.lead` 另外覆寫回 `center`。
- 圖片寬度上限（1280×720、25px 字級實測）：實拍對照 `w:790`、圖表 `w:960`、
  九宮格 `w:880`。超過就會把最後一條 bullet 推進 footer。

**驗證**：`npx @marp-team/marp-cli main.md --allow-local-files --images png`
渲染 14 張圖，逐張目視確認無溢出、footer 未被遮蓋。

**追加（14:59）**：封面第三行原本是 `### B-line: OCR, post-processing and integration`，
是隊友建立骨架時只寫 B 線留下的。deck 現在先講 A 後講 B，封面卻只寫 B-line，
台上第一句就與標題對不上，因此改為
`### A-line: image to a rectified crop  ·  B-line: OCR and post-processing`。

---
**追加（15:04）**：B 線原本沒有分隔頁，結構不對稱（A 線有 `# A-line: image to a rectified crop`，
B 線直接由 `## We own the split` 開場）。在第 9 頁「共用契約」之後補一頁
`# B-line: OCR, post-processing and integration`（`_class: lead`），deck 由 14 頁變 **15 頁**。
放在契約頁之後而不是之前，是因為契約頁是 A 交給 B 的交接，講完才知道 B 收到什麼。

---
**注意**：`project/slides/assets/*.png` **不走 Git LFS**（普通 binary，約 50–100 KB），
所以 `git lfs install` 沒裝的人也能正常 render 簡報。

---
## 2026-11-23 — 修掉 Colab 上的三個「靜默降級」（新增 `[S0-5]`、改寫 `[D1-06]` self test）

**摘要**：Colab 那份跑完 40 個 code cell、0 個 error，但**評估數字全是假的**。
`[EV]` 印出「N=5 整牌正確 100.0%」，實際上是 `gt=""` 對 `pred=""` 的空字串自我相等。
修正 `notebooks/lpr_dev.ipynb`（69 → 70 cells）並重新產生 Colab 副本。

**為什麼要做**：使用者把 Colab 跑完的輸出版本下載回來核對，發現三個缺口都不會讓
Run All 失敗，只會讓結果看起來「很好」：

| 缺口 | 現象 | 連鎖後果 |
|---|---|---|
| `easyocr` 未安裝 | `[OCR-02] EasyOCR 不可用: ModuleNotFoundError` | 每張都回空字串，**不報錯** |
| `data/labels.csv` text 全空 | `[D1-02]` 先建 100 列空白骨架 → `[D1-06]` 見檔案已存在就跳過下載 | `[INT-01]` 的 `only_labelled` 濾掉全部 100 列 → A 段完成 **0/0** 張 |
| `shared/rectified_auto/` 不存在 | `[INT-02]` 三個候選路徑全部 miss | §8/§9 悄悄退化成「前 5 張」評估 |

串起來就是：`labels.csv` 無 GT → A 段 0 張 → `[EV]` `end2end=0/0` → 退化成
`gt` 與 `pred` 都空字串 → 假 100%。

**好消息**：Colab 抽樣到的 100 張影像與本機**完全相同**（`train_IMG_1231` /
`1245` / `4540` / `4553` / `4573`…，指紋 `bd1a4489`）。所以版本差異（Python
3.13.18 vs 3.12.10）確實不影響結果，問題純粹是環境缺少東西。

**改動內容**

1. **新增 `[S0-5]`（cell 14，插在 `[S0-4]` self test 之後）**
   `Colab 環境就緒：缺什麼補什麼（本機執行時整格 no-op）`
   - `_colab_ensure_easyocr()`：try import → `pip install -q easyocr` → 再 try
   - `_colab_ensure_rectified_auto()`：`apt-get install git-lfs` → `git lfs install --skip-repo`
     → `git clone --depth 1` → `git lfs pull -I "project/shared/rectified_auto"`
     → `copytree` 到 `/content/shared/rectified_auto`
   - 主體 `if not IN_COLAB: print('本機環境，跳過')`
   - 設計原則：**只補環境，不動資料**。labels.csv 的修法屬 `[D1-06]` 的職責。

2. **改寫 `[D1-06]` self test（cell 35）**
   新增 `_filled_text_count(df)`；若「有列數但 text 全空」就判定為骨架，
   `download_labels(force=True)` 強制重抓，並印出 `筆數 | 已填 text`。
   本機行為不變（99/100 已填 → `force=False`，不會重抓）。

**為什麼放在 `[S0-5]` 而不是 `[OCR-02]` 裡面**：`[S0-5]` 在 §0 就跑完，
後面所有 import 都吃到已補好的環境；若塞進 `[OCR-02]`，它會在 §7 才 `pip install`，
而該格之後的 torch/easyocr 已經 import 失敗過了。放在最前面也讓「有沒有補」一眼可見。

**驗證**
- 本機 `nbconvert --execute`：70 cells / 41 code / **0 error**，耗時 1.6 分
- `[S0-5]` 輸出：`[S0-5] 本機環境，跳過 Colab 就緒檢查`
- `[D1-06]` 輸出：`目前 labels.csv 筆數: 100 | 已填 text: 99`、指紋 `bd1a4489`
- `debug/sync_colab.py` 重產：Colab cells 70、outputs 0

**更正上一則紀錄**：原本寫「cell 52 有 `%pip install easyocr`」是錯的，
cell 52 是 markdown，那段只是 fenced code block。已在該則加註更正。

## 2026-11-22 22:55 — 新增 requirements.txt 與 setup_env.ps1（離線交付環境）

**摘要**：為 12/18 遞交與 11/24 presentation 加上「不依賴 Google Colab」的執行路徑。
新增 `requirements.txt`（121 個解析後套件，頂層只鎖 7 個）與 `setup_env.ps1`
（建 venv → 安裝 → 註冊 kernel → 驗證）。**沒有**把 `.venv` 上傳 git。

**為什麼要做**：Colab 是 Python 3.13.18，本機是 3.12.10，且 Colab 的
`google-colab` / `numba` / `gradio` 分別把 pandas 鎖在 2.2.3、numpy <2.5、pillow <13。
硬把 Colab 對齊本機版本會打破 Colab 自身的相依鏈（實測三條衝突）。
既然 notebook 在原生 Colab 上本來就能跑，就不該為了「版本號一致」去動宿主環境。
改為提供一條本機可重現的路徑。

> **2026-11-23 更正**：上面原本寫「cell 52 有 `%pip install easyocr`」是**錯的**——
> cell 52 是 markdown，那段只是 fenced code block，永遠不會執行。實測 Colab 上
> `easyocr` 根本沒裝（`[OCR-02] EasyOCR 不可用: ModuleNotFoundError`）。
> 真正讓 Run All 不報錯的是 cell 54 的 `try/except`，代價是**靜默退化成空結果**。
> 已於 `[S0-5]` 補上安裝步驟，詳見 2026-11-23 条目。

**為什麼不把 venv 放進 git**：實測 `.venv` 是 **1437.8 MB / 51,632 個檔案**，
而 `.git` 本身已 1045.3 MB。GitHub 單檔上限 100 MB、repo 軟上限 1 GB；
Git LFS 免費額度 1 GB 儲存 / 1 GB 月流量。而且 venv **不可搬**——
`pyvenv.cfg` 的 `home`、`Scripts\python.exe` 內嵌的絕對路徑都寫死本機位置，
複製到另一台機器一定壞。1437 MB 中又有約 240 MB 是 notebook 沒 import 的
（gradio 75、sympy 66、jupyterlab 24、debugpy 31）。

**關鍵決策：opencv 只用 headless**
`easyocr==1.7.2` 硬性依賴 `opencv-python-headless`。若同時列 `opencv-python`，
dry-run 解析出 `opencv-python==5.0.0.93` + `opencv-python-headless==5.1.0.95` 兩個
distribution，會互相覆蓋 `site-packages\cv2`。查核後確認 notebook 全程用
matplotlib 顯示（`ax.imshow`），沒有任何 `cv2.imshow` / `waitKey` / `namedWindow`，
所以只保留 `opencv-python-headless==5.0.0.93`（與本機 `cv2.__version__` 5.0.0 一致）。

**驗證**：`pip install --dry-run --ignore-installed --report` 對
`requirements.txt` 解析成功，EXIT=0，121 個套件，OpenCV 只有一個 distribution。

**已知限制**：
- `setup_env.ps1` 未在「全新機器」實跑過完整安裝（會下載約 700 MB、10–15 分鐘）；
  已驗證的是**依賴解析**，不是完整安裝。
- `ipywidgets` 本機未安裝（notebook cell 30 有 `try/except` 會優雅降級）；
  清單仍列入，因為 `annotate_next()` 互動標註需要它。
- presentation 機器需先 `git lfs install`，否則 `shared/**/*.png`（345 個）不會拉下來。

---
## 2026-11-22 10:50 — 實作 [GEO-01] 真透視校正（取代純 cv2.resize）

**摘要**：把 `[GEO-01]` 從「`cv2.resize` 硬拉成 480×140」改成真正的透視變換。
由遮罩自己估四角 → `getPerspectiveTransform` → `warpPerspective`。
端到端整牌正確率 20.2% → **23.2%**（零回歸），§9 的 26 組 exact 57.7% → **65.4%**。

**為什麼要做**：舊版只是等比拉伸。斜拍或側拍的車牌被壓進 480×140 後，
字仍然是斜的、而且被非等比縮放剪切成形 —— 但 B 線的自研切字窗
（`_bands_of` / `_segs_of`）**假設字元垂直**，行投影一斜就切不出字。
實測全量 99 張的遮罩傾角：median 6.1°、p90 25.7°、max 42.3°，可見這不是罕見情況。

**為什麼用 mask 估角，而不用 `SEG_LAST_QUAD`**：

| 來源 | 問題 |
|---|---|
| `SEG_LAST_QUAD` | 它是**原圖座標**，但 `rectify()` 拿到的是已經裁切後的小圖，偏移量在契約外流失 |
| `mask` | 它就在同一張小圖上，255 = 真實車牌像素，且已通過 `[SEG-01]` 的顏色驗證 |

`rectify(plate_bgr, mask)` 的簽名不動，只靠第二個參數就能自洽。

**做法**：
1. 遮罩最大連通域 → `cv2.minAreaRect` → `boxPoints` 取四角
2. `sort_quad` 排成 左上→右上→右下→左下，`getPerspectiveTransform` 到 `PLATE_W×PLATE_H`
3. 圖像走 `INTER_LINEAR` + `BORDER_REPLICATE`；遮罩走 `INTER_NEAREST`，
   避免插值製造出「半透明的車牌像素」
4. 三道風險欄：`GEO_MIN_MASK_AREA=0.15`（遮罩佔比太低）、`GEO_AR_RANGE=(1.8, 6.0)`
   （長寬比不合理）、`GEO_MIN_SIDE=4`（短邊太小＝遮罩碎掉）→ 任一不符就退回 `cv2.resize`

**量測（99 張有標註，SEG-01 固定為新版，只換 rectify）**：

| 條件 | 舊 GEO-01 | 新 GEO-01 |
|---|---|---|
| 全體整牌正確 | 20.2% (20/99) | **23.2%** (23/99) |
| 定位命中 IoU≥0.5（30 張） | 60.0% | **66.7%** |
| 走透視校正的 67 張 | 29.9% | **34.3%** |
| 回退等比縮放的 32 張 | 0.0% | 0.0%（斷言驗證行為完全相同） |
| 格式合法比例 | 70.7% | 67.7% |

由錯改對 3 張、由對改錯 **0 張**：
- `US529`：`0S529` → `US529`（傾角 +20.5°）
- `YG6805`：`76B05` → `YG6805`（傾角 −20.0°）
- `DT3231`：`P28` → `DT3231`（傾角 +6.1°）

三張都是「斜到切不出字」的案例，正是 GEO-01 該修的錯。

**校正效果（self test，100 張全量）**：走透視校正 68 張、回退 32 張；
有校正的 68 張平均傾角 **9.5° → 0.0°**，最斜的一張由 +40.2° 拉正，有效區 0.38 → 0.89。
尺寸契約 100/100 通過。

**§9（26 組 rectified_auto）**：exact 57.7% → **65.4%**，CER 0.185 → **0.126**，valid 84.6% → 88.5%。
舊 SEG-01 → 新 SEG-01 → 新 GEO-01 的累積效果：53.8% → 57.7% → 65.4%。

**注意**：`valid` 比例從 70.7% 降到 67.7%（99 張全量），是唯一變差的一欄。
原因是校正後字元被拉正，某些原本「歪到剛好湊成合法格式」的字串變成不合法。
以整牌正確率為主要指標，這個交換是值得的，報告要如實寫出。

**已知限制**：`[SEG-01]` 會依遮罩裁緊，若遮罩本身只覆蓋車牌一部分（顏色驗證失準），
裁切階段就已經把內容切掉，校正階段無法救回。這是 SEG-01 的責任，不是 GEO-01 的。

**已重產**：`shared/stages/`（85 個 stem，`_05_rectify.png` 全部換成校正版）、
`shared/rectified_auto/`（26 組，`_index.csv` 的 `maskfill` median 0.58 → 0.79）。
stem 集合不變，隊友可直接在同一批 stem 上做前後對比。

**驗證**：`nbconvert --execute` 65 cells、0 error；全量 100 張尺寸契約 100/100；
Colab 版同步、`nbformat.validate()` 通過。

## 2026-11-22 01:10 — 實作 [SEG-01] 車牌擷取（tight crop + 真遮罩）

**摘要**：把 `[SEG-01]` 從「取 quad 外接矩形、遮罩全 255」改成真正的擷取：
四邊形往內縮 → 顏色驗證 → 只留最大連通域 → 依遮罩裁緊。
端到端整牌正確率 18.2% → 20.2%，定位命中的子集 56.7% → 60.0%。

**為什麼要做**：舊版 `segment()` 等於沒做擷取 —— 它只是把 `quad` 的外接矩形切下來，
mask 全 255 等於告訴 B 線「矩形內每個像素都是車牌」。車身、保險槓、黃線因此全部
進了 OCR，`binarize()` 把車身暗部當成前景，自研切字的列投影只剩一段，切字直接失效。
這也是隊友「乾淨裁切 8/8、pipeline 校正圖 53.8%」差距的主因。

**做法**：
1. `SEG_SHRINK=0.06` 四邊形往中心等比收縮，去掉車牌外框線
2. 依縮後四邊形的外接矩形裁切，外留 `SEG_MARGIN=0.06`
3. `fillPoly` 產生四邊形遮罩（保底）
4. 用 `plate_color_masks()`（白底 / 黃底）與四邊形取交集
5. 水平閉運算 `(15,5)` 把字元間隙縫成整塊車牌底，只留最大連通域
6. 若顏色結果 < 原多邊形面積 `SEG_MIN_KEEP=0.25`，視為驗證失敗，退回四邊形遮罩
7. 依遮罩實際範圍把影像裁緊
8. 精修後的四邊形記到 `SEG_LAST_QUAD`，供 `[GEO-01]` 做透視變換

**量測（99 張全量、走完整 A+B 線）**：

| 條件 | 舊 SEG-01 | 新 SEG-01 |
|---|---|---|
| 全體整牌正確 | 18.2% (18/99) | **20.2%** (20/99) |
| 定位命中 IoU≥0.5（30 張） | 56.7% | **60.0%** |
| 定位失準 IoU<0.5（69 張） | 1.4% | 2.9% |
| 遮罩有效區 median | 1.00（全 255） | **0.59** |

由錯改對：`VF9219`（WF→VF）、`WH961`（W6→WH961）、`VC3874`、`AL139`
由對改錯：`YE2881`（尾字被裁掉）、`DM6368`（多一個 A）—— net +4，但仍是 2 進 2 出。

**§9（26 組 rectified_auto）**：exact 53.8% → **57.7%**，CER 0.177 → 0.185，valid 84.6% 不變。
CER 微升是因為命中的張數變多、把較難的案例納入平均。

**已重產**：`shared/stages/`（255 檔，100 張全有輸出）、`shared/rectified_auto/`（26 組，
`_index.csv` 多了 `maskfill` 欄）。stem 集合不變，隊友可直接前後對比。

**驗證**：`nbconvert --execute` 65 cells、0 error；Colab 版同步、`nbformat.validate()` 通過。

## 2026-11-21 23:10 — 合併隊友的 [OCR-01]/[OCR-02]、改用 git LFS 同步

**摘要**：把隊友（shing）寄來的 §6 OCR 實作合併進 dev notebook，並修掉兩個接不上的問題。
另外檔案同步從 rar 改為 git + Git LFS，`shared/` 的 309 張 PNG 已上 master。

**合併內容**：
- `[OCR-01]`：`norm_illum()`（形態學閉運算估背景 → 相除，消底色明暗不均）+
  `binarize()`（中值濾波 → 光照歸一化 → OTSU INV → 極性校正 → 開運算 → mask 歸零）
- `[OCR-02]`：自研切分 `_bands_of`（行）/`_segs_of`（字元）/`_split_char`（黏連切開），
  EasyOCR 只負責認字；中文複核走 `cn=True` 懶載第二組模型

**修掉的兩個問題**：

1. **`torch` 未 import** — 原文 `gpu=torch.cuda.is_available()`，但 cell 內從沒 `import torch`。
   在他 notebook 因為別處 import 過所以沒炸，搬過來就是 `NameError`。
   改為包一層 `_gpu_available()`，`torch` 缺席時回 `False`。
2. **self test 向前引用** — 我第一版 self test 用 `list_stage_stems()`，那支函式在 §8 才定義。
   改成自己 glob 掃 `shared/stages/`。（同一個坑第二次踩，已記在教訓裡。）

**本機環境**：`easyocr 1.7.2` + `torch 2.15.0+cpu` + `torchvision`。
`pip install easyocr` 會想升級 `opencv-python`，撞到 `cv2.pyd` 被 kernel 佔用（WinError 5），
改用 `--no-deps` 再補 `torchvision`/`ninja`/`scikit-image` 繞過。
第一次跑 `easyocr.Reader` 下載模型被本機 SSL 憑證攔截，手動 curl 兩個 .pth 到
`~/.EasyOCR/model/` 後正常（Colab 不會有此問題）。

**量測（抽驗前 6 張，全部是 A 段 accepted）**：字串完全正確 1/6。
其中 `LWF9219` vs GT `VF9219` 只差一字，其餘多為定位錯框或切字只剩 1 個字元。
⚠️ 這 6 張是**依檔名排序的前 6 張**，含錯框案例，不能當 §6 準確率。
隊友在他那份乾淨裁切圖上是 8/8。

**Git LFS**：`.gitattributes` 加 `project/shared/**/*.png filter=lfs`；
`.gitignore` 的 `shared/` 改為只忽略 `shared/bridge/`（本機訊息狀態）與 `project/shared.rar`。
309 個 PNG 實際只產生 179 個 LFS object（mask 大量重複），共 13 MB。

## 2026-11-21 21:55 — 接通隊友 bridge、修正 A 段示範輸出污染、匯出 26 組真實校正圖

**摘要**：讀取隊友（shing）2 則訊息並回覆；同時發現 A 段把 GT-bbox 示範輸出寫進
`shared/stages/`（隊友正在讀的同一個目錄），已分離。真 pipeline 全量跑出 **85/99 通過門檻**，
其中 **42 張（49.4%）的 top-1 定位框真的蓋到車牌**。另外匯出 26 組「定位正確」的
校正圖到 `shared/rectified_auto/` 給隊友調 §6。

**原因（A 段污染）**：`[INT-01]` self test 用 `export_dataset_frontend(use_gt_bbox=True)`
驗證 A→B 交接，預設目錄就是 `shared/stages/`。但那是**用答案裁的圖**，
和真 pipeline 輸出混在一起後，B 線無法分辨手上那張圖是不是答案，
§9 的數字就永遠說不清 —— 這比程式錯更危險，因為它不會報錯。

**變更**：
- `[INT-01]` self test：示範模式改寫到 `debug/demo_gt/`，並新增真 pipeline 全量輸出
- `shared/rectified_auto/`：26 組真 pipeline 校正圖（含 `_mask.png`）＋ `_index.csv`＋README
- `README` 明寫「這批有選擇偏差，不能當 §9 分母」

**量測（重要，報告要引用）**：

| 指標 | 數值 |
|---|---|
| 真 pipeline 通過信心門檻 | 85 / 99 = **85.9%** |
| 通過者中 top-1 IoU ≥ 0.5 | 42 / 85 = **49.4%** |
| 通過者平均 IoU | 0.418 |
| 被拒 14 張，其中其實有正解 | 6 張（門檻偏保守） |

⚠️ **85.9% 不是定位準確率**。門檻擋的是「低信心」，不是「錯誤」。實際能用的
只有 49.4%，也就是全體約 42%。報告不可寫 85%。

**Bridge**：寄出 #4（§5 交接 / §6 輸入），已 `ack` 到 #3。訊息內容包含
mask 語意（255=有效區）、檔名規則、以及「GT 裁切圖不可算準確率」的明確警告。

**驗證**：`nbconvert --execute` 65 cells、0 error；Colab 版同步、`nbformat.validate()` 通過。

## 2026-11-21 21:15 — 實作 `[LOC-01]` / `[LOC-02]` 車牌定位

**摘要**：把兩個定位 stub 換成可運作的實作，並建立「用 `labels.csv` GT 量測 recall」
的評估流程。全 99 張實測：**recall@1 = 30.3%、recall@5 = 48.5%、平均最佳 IoU = 0.411**。

**原因**：`[LOC-01]`→`[GEO-01]` 全是 stub 是全案唯一真阻塞點。A 段只能靠 GT bbox 示範，
真實 pipeline 一律「定位失敗」，B 線也拿不到真實輸入。

**試過但不採用的路線（實測數據，報告可直接引用）**：

| 策略 | recall@IoU0.5 |
|---|---|
| 色彩遮罩 `v>130`（課本常見值） | 24.2% |
| Canny / Sobel 邊緣 + 多尺度閉運算 | 9.1% |
| MSER 連通區域 | 0.0% |
| MSER 字元 + 分組成文字行 | 23.2% |
| blackhat 字元群組 | 7.1% |
| **色彩遮罩 `v>220` + 水平閉運算 (21,5)** | **53.5%（候選層 recall）** |

**關鍵發現（診斷圖 `debug/loc01/mask_diag.png` 證實）**：
亮度門檻是決定性參數。停車場的淺灰地面在 CLAHE 提亮後落在 `v≈150~200`，
用寬鬆門檻會讓「車牌 + 地面」黏成同一個連通域，`minAreaRect` 於是框住整片地板。
車牌是畫面中最亮的區域之一，門檻拉到 220 反而乾淨：`v>130→24%`、`v>180→34%`、
`v>220→53.5%`、`v>250→52.5%`。

**變更**：
- `[S0-2]` 新增定位參數群：`LOC_V_WHITE=220`、`LOC_CLOSE_K=(21,5)`、`LOC_AR_*`、
  `LOC_SCORE_W`、`LOC_BORDER_PENALTY=0.55`、`LOC_ACCEPT_SCORE=0.60` 等
- `[LOC-01]`：`plate_color_masks()` / `quads_from_mask()` / `localize_candidates()`。
  只做形狀合理性過濾，不評分（評分屬 `[LOC-02]`）
- `[LOC-02]`：五特徵（aspect / area / fill / edge / contrast）
  **同張圖內 min-max 正規化**後加權，再乘上貼邊懲罰，最後 NMS + top-k
- `[INT-01]` `run_frontend()` 加信心門檻：top-1 < `LOC_ACCEPT_SCORE` 即判定位失敗、不寫檔
- `[SEG-01]` / `[GEO-01]` self test 改為吃 `pick_sample_image()` 與 `[LOC-02]` 的 top-1，
  不再依赖不存在的 `TEST_IMG`

**修掉的 bug**：
- 第一版評分用**絕對值**（`edge/0.18`、`contrast/70` 直接 clip），亮圖裡所有候選都頂到
  1.00 → 完全沒有鑑別力，左上角一塊亮天花板以 `area=1.00` 排到第一。
  改為同張圖內互相比較後 recall@1 由 17.2% → 25.3%
- 面積項原本「越大越好」，導致貼邊的亮塊勝出。改為對數高斯，偏好「佔畫面約 3%」，
  並加貼邊乘性懲罰 → recall@1 25.3% → 30.3%、recall@5 45.5% → 48.5%
- A 段原本會把 top-1 垃圾（天花板）寫進 `shared/stages/` 給 B 段，現在被門檻擋住

**已知限制（報告的 future work）**：
- 遠景停車場照片車牌僅 44×30 px，與背景雜訊同級，目前抓不到
- 深色車身上的白牌在 `v>220` 下容易只剩一小塊
- GT 是**軸對齊框**，候選是**旋轉框**，斜拍車牌天生 IoU 上限約 0.5~0.6。
  因此定位指標應以「端到端字串正確率」為最終依據

**驗證**：`nbconvert --execute` 65 cells、0 error；Colab 交付版已同步並通過 `nbformat.validate()`。

## 2026-11-21 19:40 — 依隊友要求把 §8 整合拆為 A 段／B 段（`INT-01` / `INT-02`）

**摘要**：隊友希望整合分成兩半，讓 B 線可以獨立開發。§8 原本是單一 `run_pipeline()`
一次跑完 A→B 全部階段，現在改為：A 段（新 `§5.5`）負責定位→擷取→校正並把中間狀態
寫成 PNG；B 段（`§8`）用 `glob` 掃 `shared/stages/` 讀回來做 OCR 與後處理。
notebook 由 62 → 65 cells。

**原因**：B 線（`§6` OCR）若只能等 A 線全部做完才能開始，等於整條線被 `[LOC-01]`
阻塞。拆開後 B 線可以直接拿 A 段的輸出檔開發，兩邊用「檔案」而不是「函式呼叫」溝通。

**變更**：
- `[S0-2]`：新增 `STAGE_DIR = shared/stages`，並加入 `os.makedirs` 清單
- 新 `§5.5`（markdown + `[INT-01]` + self test）：
  - `run_frontend(img, quad)`：前處理→定位→擷取→校正，回傳各階段影像
  - `export_frontend()` / `export_dataset_frontend()`：寫檔版，出口是檔案
  - `EXPORT_STAGES`：只寫 `04_segment` / `05_rectify` / `05_rectify_mask`。
    原本連 `01_input`~`03_localize` 都寫，每張 2 MB（2 張就 7.3 MB）；
    收斂後每張 3 檔、共 350 KB，B 段也用不到前三個階段
  - `use_gt_bbox=True` 示範模式：`[LOC-01]` 完成前先驗證 A→B 交接機制
- `§8` 改寫為 `[INT-02]` B 段：
  - `list_stage_stems()`：`glob` 掃 `*_05_rectify.png`，缺檔即視為 A 段失敗
  - `load_stage()`：讀回階段圖，缺 mask 時用全 255（等同無 mask）
  - `run_backend(stem)`：讀檔 → `recognize` → `postprocess`
  - `run_dataset_backend()`：批次版
  - `run_pipeline()` 保留為「記憶體版」，供 §9 評估與單張推論
- Colab 交付版同步：65 cells、0 outputs、`nbformat.validate()` 通過

**修掉的 bug**：
- `load_image()` 會把最長邊縮到 1280，但 `labels.csv` 的 GT bbox 是**原始解析度座標**
  （最大 4032）。示範模式直接拿 bbox 去切圖 → 切到影像外 → `plate` 是空陣列 →
  `cv2.resize` 丟 `Assertion failed (!ssize.empty())`。
  修法：新增 `_image_size()`（只讀檔頭，用 PIL 不解碼整張圖），
  在 `export_frontend()` 內把 quad 依 `img.shape / 原始尺寸` 換算，
  並在 `run_frontend()` 加上「擷取區域為空」的防護，回傳可讀的失敗原因。

**驗證**：
- `nbconvert --execute` 全 notebook 65 cells，0 error
- 示範模式產出 2 個 stem（`train_IMG_1231…`、`train_IMG_1245…`）；
  B 段正確讀回 `(140, 480, 3)`，`text=''`（`§6` 尚未實作，符合預期）
- 目視確認交接圖正確切到車牌：`RDA·2388`、`960·GKF`
- 檔名帶空格或用 `pick_sample_image()` 都可運作

**注意**：
- 示範模式的輸出**不可用於報告或 §9 準確率**，那等於拿答案做題
- `[LOC-01]` 實作後，`use_gt_bbox` 應改回 `False`

## 2026-11-21 17:10 — 新增 `tools/export_rectified.py`，解除 B 線（§6 OCR）阻塞

**摘要**：B 線反應 `shared/rectified/` 是空的、無法開始 §6。新增匯出工具，
用 `labels.csv` 的 GT bbox 產生符合契約的校正圖（480×140 PNG + mask），
並補上 `shared/rectified/README.md` 與 `TASK_DIVISION.md §3.3` 的格式契約。

**原因**：notebook 只在文件寫「§5 存到 `shared/rectified/`、§6 讀它」，
**從來沒有任何寫檔的程式碼**，而 `[LOC-01]`→`[GEO-01]` 又全是 stub，
所以那個目錄一直是空的。B 線等於在等一個不存在的交付物。

**變更**：
- 新增 `tools/export_rectified.py`：`--list` / `--limit N` / `--all` / 檔名關鍵字
- 新增 `shared/rectified/README.md`：檔案契約、限制、§6 起點程式碼
- notebook「B 線」markdown cell 補上工具用法與三條紅線（見下）
- `TASK_DIVISION.md §3.3` 新增「`shared/rectified/` 的格式契約」小節

**關鍵設計決策 —— 為什麼不直接 resize 到 480×140**：
這批資料 `AR`（`w/h`）中位數只有 **1.52**，99 張裡有 49 張 < 1.5，
代表車牌在原圖中普遍斜拍。第一版直接 `cv2.resize` 的結果是
`RDA2388`（原始框 953×990）被壓成 480×140，字高只剩原本的 1/7，整個變扁 ——
B 線拿這種圖調 OCR 參數會全部調歪。改為**等比縮放 + 置中補灰邊**，
保留原比例、字不變形，代價是較方的車牌左右留白。

**試過但放棄的方案**：以色彩遮罩（白底/黃底）+ `minAreaRect` 自動找車牌四邊形
再做透視變換。失敗原因：車身同樣是銀白色，色彩遮罩分不開，
`minAreaRect` 會抓到整個裁切區（`RDA2388` 的 area% 達 0.78），
6 個測試樣本中 4 個失敗。真正的透視校正留給 `[GEO-01]`。

**驗證**：完整執行 62 cells / 35 code cells，0 error；輸出 4 張範例
（`GN2896` 白、`YL7582` 白、`GT3500` 黃、`GG1996` 白）經目視確認字未變形；
mask 白佔比與「真實影像區」吻合（`GN2896` 87.9% = 161/629 等比重疊後的高度佔比）；
兩份 notebook 通過 `nbformat.validate()`。

---

## 2026-11-21 16:08 — 難度標記語意落地：文件、常數、`label_progress()` 判定

**摘要**：補齊 `difficulty` 的語意說明（`normal` / `hard` / `unreadable` / `not_plate`），
把難度值收斂成共用常數，並修正 `label_progress()` 會把 #16 永遠算成「未標註」的問題。

**原因**：`unreadable` 那一列的 `text` 刻意留空（反光遮蔽、人眼不可判讀），
但 `label_progress()` 只用「`text` 是否空白」判斷，導致明明 100 張全數審核完成，
進度表卻永遠顯示 99/100。同時 `save_label()` 與 `annotate_next()` 仍在用
`easy` 這個實際資料中不存在的值。

**變更**：
- `[S0-2]` 新增 `LABEL_DIFFICULTIES`、`UNSCORABLE_DIFFICULTIES` 兩個常數，
  作為全 notebook 唯一的難度值來源，避免各處硬寫字串
- 「`labels.csv` 欄位」markdown cell：`difficulty` 改列四種值，並新增語意表
  （哪一種計入 §9 準確率、為什麼 `unreadable` 不填猜測值）
- `[D1-03]` 新增 `_is_labelled()`：「`text` 非空 **或** `difficulty` 屬不可評分」才算已處理；
  `label_progress()` 與 `next_unlabeled()` 都改用它
- `[D1-03]` `save_label()` 允許 `unreadable` 留空；`annotate_next()` 難度選單
  由 `easy/normal/hard` 改为 `LABEL_DIFFICULTIES`
- `[EV-01]` `EVAL_EXCLUDE_DIFFICULTY` 改為引用 `UNSCORABLE_DIFFICULTIES` 的別名
  （保留舊名，既有說明與報告不用改），`evaluable_labels()` 仍為空殼，留待 §9
- `TASK_DIVISION.md` §1 欄位表與 §7.3 / §7.4 同步更新，兩項待辦標為完成

**驗證**：完整執行 35 個 code cell，0 error；`label_progress()` 由 99/100 修正為
**100/100 已標註**；`labels.csv` 仍為 100 列、99 有效標註、排序正確；
兩份 notebook 均通過 `nbformat.validate()`。

---

# AI 編輯紀錄（`lpr_dev.ipynb`）

> **用途**：記錄每一次由 AI 執行、對 `notebooks/lpr_dev.ipynb` 的修改**摘要與原因**。
>
> **詳細內容由 git 承載**：本檔不重複描述改了哪幾行、前後對照是什麼 —— 用 `git show <hash>` 就看得到完整 diff。
> 本檔只回答兩個問題：**為什麼改**、**大致動了什麼**。
>
> **重要**：本檔不會提交給評閱老師，也不屬於 notebook 內容。

## 紀錄規則

1. 每次 AI 修改 notebook 就新增一筆，**插在 `## 紀錄` 最上方**（最新在上）。
2. 每筆只寫四項：**標題**（編號 + 一句話）、**Commit**、**為什麼改**、**摘要**。
3. **摘要寫「動了什麼」，不寫驗證過程**；除非驗證結果改變了結論，才用一句話帶過。
4. 長的列舉壓成一行，用 `｜` 分隔；不要為每項另開子清單。
5. 使用者本人手動修改不需要記錄（git diff 即為紀錄）。
6. 若單筆真的需要細節（例如決策有取捨），把細節寫在 git commit message，不寫在這裡。

## 20. 100 張標註審核完成；預留 `unreadable` 排除介面（未實作）

**為什麼改**：使用者用 Gradio 審核工具逐張核對完 100 張，修正了 4 筆（#26 判定改為非車牌、
#41 `HH6729`→`HH6728`、#55 `PO3479`→`PD8479`、#73 `MZ8208`→`NZ8208`）並補了 17 筆 `front_rear`。
其中 #16 因反光遮蔽、人眼亦不可判讀，`text` 必須留空 —— 但留空會讓 §9 的準確率無法計算、
`label_progress()` 又會永遠把它算成「未標註」。使用者要求「加入計劃並在程式碼預留接口，但先不弄」。

**摘要**：
- `TASK_DIVISION.md` 新增 §7「標註例外處理（已納入計劃，尚未實作）」：
  #16 排除、#26 保留為失敗案例的差別、4 項待辦、報告寫法
- `[EV-01]` 預留 `EVAL_EXCLUDE_DIFFICULTY = ('unreadable', 'not_plate')` 與
  `evaluable_labels()` 空殼（原樣回傳，不改變現有行為），避免實作 §9 時找不到插入點
- **未動** `label_progress()` 判定邏輯與「`labels.csv` 欄位」表格 —— 依使用者指示本次不實作

**驗證**：完整重跑 0 error；`[D1-03]` 統計 main 100 張、已標註 99、未標註 1，
那 1 張即 #16（預期行為，待 §7 待辦修正後會消失）。

## 19. 排序改回檔名字串、100 張車牌 `text` 全部填寫

**為什麼改**：第 18 筆把排序鍵改成「取 `IMG_` 流水號做數值排序」，但使用者實際操作時是
**開著檔案總管、照資料夾顯示的順序往下填**，而檔案總管是按整個檔名字串（最左字元起）排序。
數值排序會讓 `train_IMG_4540_jpg...`（無 `_JPG`）插到不同位置，順序對不上就得一直回頭找圖。
另外使用者要求由 AI 直接完成 100 張的車牌字串填寫。

**摘要**：
- `file_sort_key()` 改為直接回傳檔名字串（最左字元起比對，與檔案總管一致），移除流水號解析
- `[D1-02]`／`[D1-03]` 排序呼叫改用 `sort_values('file')`；`labels.csv` 已依新序重排
- `data/labels.csv` 100 列 `text` 全部填寫，`difficulty` 分級：
  `normal` 89 張、`hard` 9 張（模糊／被切邊／被遮蔽）`unreadable` 1 張（#16 `UJ1?67` 中間字被反光白塊蓋住）、
  `not_plate` 1 張（#26 標到前保桿上的 `ARTELLIA` 字樣，是資料集誤標，可作為 §9 失敗案例）

**驗證**：完整重跑 0 error；`[D1-02]` 印出「指紋相符，重跑不會動到已填的 text」，
`[D1-03]` 統計 main 100 張、已標註 98、未標註 2（即上述 `unreadable` 與 `not_plate` 兩張）。

## 15. `[D1-02]` 修正 labels.csv 不斷累積、抽樣改為跨機器決定性

**為什麼改**：原本「舊有但這次沒抽到的列一併保留」的設計，是為了不弄丟已填的車牌字串，
但實際重跑時會每次再疊 100 列（實測已累積到 193 列），導致 `labels.csv` 與「main 100 張」
契約不符，`[D1-03]` 的標註進度與 §9 評估也會算錯。另外抽樣順序依賴 `os.walk` 的檔案系統
順序，本機與 Colab 會抽到不同的 100 張，`text` 欄位就會對錯影像。

**摘要**：
- `import_coco()` 改為：`labels.csv` 必須剛好等於本次抽樣結果，本次沒抽到的舊列一律移除
- 移除前若發現該列已填 `text`，先印出警告並列出檔名，避免靜靜刪掉人工標註
- 抽樣池 `pool.sort(key=檔名)`、`os.walk` 加 `dirs.sort()` / `files.sort()`，確保跨平台一致
- 新增抽樣指紋（`hashlib.md5` 取前 8 碼），印在輸出供本機與 Colab 對照
- `[S0-1]` 補 `import hashlib`

**驗證**：重跑兩次皆 0 error，`labels.csv` 穩定 100 列、100 個不重複檔名，指紋同為 `bd1a4489`。

## 16. 抽樣指紋鎖＋`[D1-06]` labels.csv 的 Drive 收送

**為什麼改**：`labels.csv` 的 `text` 欄是「第 N 張影像的正確答案」，只對抽樣出來的那 100 張有效。
若資料集版本或 `RANDOM_SEED` 被改動，抽到另一批影像，`text` 就會全部對錯圖片 —— 程式仍可跑，
但 §9 的準確率從此沒有意義。同時，`labels.csv` 是人工成果、不從資料集取得，需要一個跨機器收送的管道。

**摘要**：
- `[D1-01]` 新增 `_stamp_fp()` / `_labels_fingerprint()`，指紋以 `fp=xxxxxxxx` 記在 `note` 欄
- `[D1-02]` 抽樣後先算指紋並與 `labels.csv` 比對：不符就**拒絕重抽**並列出原因；
  確定要換一批須顯式設 `FORCE_RESAMPLE = True`
- `[D1-02]` 移除不在本次抽樣中的舊列時，連同 `data/images/` 的影像檔一併刪除
  （只刪舊 `labels.csv` 有登記的，自訂測試圖不受影響）
- 新增 `[D1-06]`：`download_labels()` 從 Drive 取回 `labels.csv`（免掛載、繼承病毒掃描警告處理），
  `save_labels_to_drive()` 回存（Colab 寫入掛載的 Drive，未掛載則用 `files.download()`）
- `[D1-06]` 下載後比對遠端與本機指紋，不符會警告
- `### 資料集取得方式` 表格補上第 4 步 `[D1-06]`

**驗證**：62 cells、0 error；重跑兩次 `labels.csv` 穩定 100 列、`data/images/` 100 張、
指紋皆為 `bd1a4489`，第二次執行印出「指紋相符，重跑不會動到已填的 text」。

## 17. `[PRE-01]` 前處理實作（CLAHE + 雙邊濾波 + unsharp）

**為什麼改**：`[PRE-01]` 原本是原圖回傳的佔位。§3 定位要靠邊緣訊號，
而這批資料集有大量背光、車身反光、夜間與通訊軟體壓縮的影像，不先補光照會讓
Canny 在暗側完全抓不到車牌邊界。同時 §0 沒有任何「挑測試圖」的工具，
各節 self test 只能靠 `TEST_IMG` 一個固定路徑，資料一換就全部略過。

**摘要**：
- `[S0-4]` 新增 `pick_sample_image(seed=0)`：優先 `TEST_IMG`，否則從 `data/images/`
  依檔名排序取第 seed 張。各節 self test 因此能直接跑真圖。
- `preprocess()` 管線＝光照補償 → 去噪 → 銳化，三個步驟各有旗標（供 ablation）
- `_compensate_illumination()` 在 LAB 的 L 通道做 CLAHE（clip=2.0, grid=8×8）。
  只動亮度不動 a/b，避免白底車牌被推藍、黃底跑色而影響正反面判斷。
- `_denoise()` 用雙邊濾波而非高斯：高斯會把車牌邊界一起糊掉，而邊界正是 §3 要用的訊號。
- `_sharpen()` unsharp mask，amount=0.6。
- 契約檢查寫進 self test：尺寸、dtype 不變，並輸出對比／邊緣密度／平均 BGR 偏移
- self test 附 ablation 表（四種組合的 std 與 edge%），報告可直接引用

**驗證**：0 error。測試圖 `train_IMG_1231_JPG.rf.4427...jpg`（960×1280）
邊緣密度 4.89% → 9.33%、對比 59.0 → 57.1、平均 BGR 偏移 [18,18,18]
（僅分區重分配，全圖平均色不變）。目視確認車牌 `RDA-2388` 更清晰且無偏色。

## 18. `labels.csv` 依檔名數值排序＋車牌字串正規化

**為什麼改**：使用者開始手動填 `text` 時發現 CSV 的順序不是依檔名 —— 因為 `[D1-02]`
是固定種子隨機抽樣，列序就是抽樣順序。逐張填寫時要回頭找圖很痛苦。
另外香港車牌印刷常見 `RDA•2388`、`RDA-2388`，但中間那個是排版分隔、不是字元；
原本只濾掉空白與連字號，圓點會被留下來，導致 §9 評估全部判成錯誤。

**摘要**：
- `[D1-01]` 新增 `file_sort_key()`：取 `IMG_` 後面的流水號做**數值**排序
  （字串排序會得到 IMG_1000 < IMG_1231 < IMG_4568 … 看起來仍是亂的）；無流水號者排最後
  - 放在 `[D1-01]` 而非 `[D1-03]`，因為 `[D1-02]` 先執行、不能引用後面才定義的函式
- `[D1-01]` 新增 `normalize_plate_text()`：NFKC 全形轉半形 → 全大寫 → 只留英數與中文
- `[D1-03]` 新增 `sort_labels_csv()`；`next_unlabeled()` 改為依數值順序取下一張
- `[D1-02]` 寫檔前先排序，打開 CSV 就是順的
- `[D1-03]` `save_label()` 改用 `normalize_plate_text()`
- `### labels.csv 欄位` 補上「車牌字串寫法」小節（圓點／連字號／粵Z 中文）

**驗證**：0 error。`RDA•2388`→`RDA2388`、`RDA-2388`→`RDA2388`、`rda 2388`→`RDA2388`、
`粵Z·1234`→`粵Z1234`、`AB１２３４`→`AB1234`（全形）。現有 `labels.csv` 已重排，
1 筆已填內容保留。

---
---
---
---
---

## 紀錄

> 排序：**最新在最上**。標題前的編號是加入順序，數字越大越新。

### 14. D1-05 改為 Drive 連結下載；以真實資料集驗證整條流程（e9158e3）

- **為什麼改**：使用者要求「用連結下載，不要綁定 Google Drive 掛載」。同時取得真實資料集連結（1.02 GB，hk-fszrn v2），首次能用真資料驗證 §1。
- **摘要**：`[D1-05]` 由「掛載 + 同步資料夾」改為「分享連結下載」，支援 `/file/d/<ID>/view`、`open?id=`、純 ID 三種輸入，自動處理大檔的病毒掃描警告頁｜`[D1-04]` 抽出 `has_coco`／`_download_stream`／`extract_coco_zip`／`_merge_into` 供兩者共用，下載改串流寫入並印進度｜修掉三個只在真資料才會出現的錯：self test 向前引用（`check_raw_dir`／`label_progress`）、`import_coco` 未建 `DATA_DIR`、車牌類別多算 Roboflow 自動產生的父類別｜`PLATE_CATEGORY='license_plate'`｜`.gitignore` 補 `data/raw`、`data/labels.csv`（1 GB 不可進 git）。

### 13. import_coco 加入類別篩選；新增 Roboflow 直連下載（1171ae6）

- **為什麼改**：使用者提供 Google AI Mode 產生的下載腳本，檢查後發現兩個真問題 —— ① 腳本把 API key 寫在 notebook（要遞交給評閱者，等於交出帳號額度）② 取「前 100 張」不是隨機，100 張極可能同一場景。檢查過程另外發現**我們自己**的漏洞：`import_coco()` 只取面積最大框、不篩類別，而 B 集所在 workspace 是 `safety-helmet-detection`，很可能抓到安全帽而非車牌。
- **摘要**：新增 `_plate_category_ids()`，多類別時只取車牌類別，`PLATE_CATEGORY` 留空則自動判斷｜`check_raw_dir()` 加「車牌類別」欄並在猜不出時警告｜`import_coco()` 重跑保留已填的 `text`/`front_rear`/`difficulty`｜新增 `[D1-04] download_coco()` 用 Roboflow 公開直連網址下載（免 API key），解壓後壓平外層資料夾、已存在不重下｜原 Drive 版本改為 `[D1-05]` 備援｜`RAW_DIR` 從 `[D1-02]` 移到 `[S0-2]`（`[D1-04]` 比 `[D1-02]` 先執行，會 NameError）。

### 12. 新增從 Google Drive 取得資料集（8b62b3d）

- **為什麼改**：最終遞交版本是 Google Colab 那份，資料集應放雲端而非下載到本機；隊友複製 notebook 也要能取得同一份資料，因此需要一個「填連結就能用」的載入 cell。
- **摘要**：新增 `[D1-04]`（`mount_drive`／`locate_dataset_dir`／`sync_from_drive`）｜Drive 資料夾含 `raw/`、`images/`、`labels.csv` 任一即同步到工作目錄，預設不覆蓋、`force=True` 強制更新｜`labels.csv` 內容相同時略過、不同才備份後覆蓋｜`DRIVE_DATASET_DIR` 留 placeholder 待填｜本機執行自動略過掛載｜§1「資料集取得方式」改寫為評閱者／組員／無資料三種視角。

### 11. 匯入張數改為總量 100，並加入 data/raw 結構檢查（d08c51a）

- **為什麼改**：使用者決定「B 集抽 100 張」使用；且 Roboflow 解壓後可能多包一層資料夾，需要先確認結構。
- **摘要**：`[D1-02]` 由「每切分 25 張」改為「總量 100 張、固定種子跨 split 隨機抽樣」｜新增 `check_raw_dir()` 遞迴搜尋 COCO 標註並核對實際影像數｜新增車牌寬度門檻 `MIN_PLATE_W=40` 與跳過統計｜§1、引用表、`TASK_DIVISION.md` 張數同步為 100。

### 10. 修正 AI 編輯紀錄被清空的意外（e0260fe）

- **為什麼改**：回填 commit hash 時以單行鏈式寫法先開 `'w'` 再讀同檔，導致紀錄被截斷成 0 bytes。
- **摘要**：從 `65b4913` 還原全文｜改為「先讀 → 記憶體處理 → 後寫」｜補回第 9 筆 hash｜條目依編號重新由新到舊排序。

### 9. 加入資料集來源與引用（CC BY 4.0 要求）（65b4913）

- **為什麼改**：使用者提供 Roboflow 的 Cite This Project 頁面，兩個資料集皆為 CC BY 4.0，需標明出處。
- **摘要**：§1 新增「資料集來源與引用」小節，含兩份資料集的用途／張數／授權表與主集的 BibTeX；標明兩者皆只提供邊界框、`text` 由本組人工填寫。

### 8. 資料集定案：main/external 雙集 + D1-02/D1-03 工具（1a1bc8e）

- **為什麼改**：使用者決定「B 集（1,491 張）為主 40–50 張、A 集（33 張）為 external 10–15 張」，並要求提供標註工具；同時決定「先單一車牌但 labels.csv 預留欄位」。
- **摘要**：`LABEL_COLUMNS` 加 `plate_idx`、`split`｜§1 改寫為雙測試集說明｜新增 `[D1-02]` COCO 匯入（多車牌取面積最大、缺圖跳過）與 `[D1-03]` 半自動標註（`label_progress`／`next_unlabeled`／`save_label`／`annotate_next`）｜`S0-1` 加 `shutil`、`re`｜目錄與進度同步｜`TASK_DIVISION.md` 加欄位表｜AI 聲明補回資料集那一列。

### 7. AI 聲明「開發用內容標記制度」列措辭（c62a5ae）

- **為什麼改**：使用者指定把「不是要給評閱老師看的內容」改為「開發用標示內容」。
- **摘要**：該列「我給 AI 的輸入」欄改寫為「要求『開發用標示內容』都要額外標示，指明是開發時用、未來需刪除或更改」。

### 6. Colab 交付前健檢（e5f3b75）

- **為什麼改**：要貼到 Colab 讓隊友複製開工，要求最終檢查。發現 4 項會影響隊友的問題。
- **摘要**：清除全部 code cell 輸出（殘留 `C:\Users\honok\...` 本機路徑）｜`kernelspec` `cis342` → `python3`（Colab 無此 kernel）｜`[S0-4]` 加入 `use_cjk_font()`（Colab 缺 CJK 字型，圖表中文會變方框）｜補上 §9 的 self test（其餘 8 節都有）。

### 5. 新增「目錄」cell（e76a49c）

- **為什麼改**：使用者要求把目錄加回標題頁之後。
- **摘要**：新增 `## 目錄`，分「前置文件」與「主體章節」兩張表；負責人一律寫姓名不寫 A／B 線。「使用規則」的必須保留清單加入 `## 目錄`。

### 4. AI 聲明「表格格式」列改寫（c426e5c）

- **為什麼改**：原寫法「要求依該文件表格格式改寫」不準確 —— 那份 PDF 是使用者提供的**格式範例**，不是要照抄的規定文件。
- **摘要**：該列及相關欄位改為「提供一份 AI 使用聲明的格式範例…依該範例的表格格式製作」。

### 3. 修正 AI 聲明重複（001ee7f）

- **為什麼改**：前一輪改寫時新增了新版 cell 卻未刪除舊版，同一節出現兩份。
- **摘要**：以 markdown 第一個 `## ` 標題為 key 去重，保留第一次出現者；45 → 47 → 45 cells。

### 2. 移除 AI 聲明中的「資料集來源評估」列（001ee7f）

- **為什麼改**：使用者選擇「等資料集最終確定後再寫入聲明」。
- **摘要**：刪除該列，其餘 5 列不動。

### 1. AI 使用聲明改寫為如實紀錄（001ee7f）

- **為什麼改**：使用者指出隊友的聲明應該是空的（內容都是使用者做的），並要求四欄如實填寫、不知道的直接問。
- **摘要**：Ho Nok Hei 一節由 6 列精簡為 5 列，驗證欄如實寫「本人尚未親自執行」；Li Chi Shing 一節改為空白模板並註明請勿代填。
## 2026-11-22 14:10 — LOC 門檻階梯（v>170 + v>220）

**摘要**：把 `[LOC-01]` 的單一白底門檻 `LOC_V_WHITE=220` 擴成兩階門檻
`LOC_V_LADDER=(170, 220)`，低門檻負責曝光不足的車牌，高門檻負責乾淨背景。
各階遮罩獨立產生候選，再由 `[LOC-02]` 的字元列特徵統一評分。
99 張 recall@1 48.5% → **51.5%**；recall@k 57.6% → **60.6%**；
平均最佳 IoU 0.480 → **0.503**。

**為什麼做**：門檻掃描證明單一門檻有漏，但門檻聯集可以補回大部分曝光不足案例。
跨門檻聯集上限為 recall@k 67.7%；三階（150/180/220）候選較多，但實測會被
同張圖內 min-max 正規化稀釋，沒有贏過兩階。

**量測**：

| 條件 | recall@1 | recall@k | 平均最佳 IoU |
|---|---|---|---|
| 單一 220 + 字元特徵 | 48.5% | 57.6% | 0.480 |
| 220+170 門檻階梯 | **51.5%** | **60.6%** | **0.503** |

端到端整牌正確（99 張）：38.4% → **40.4%**。
淨變化：對 +TB6248、+RE4430，錯一張回歸 MJ5541，淨 2 張改善。

**§9（26 組 rectified_auto）**：exact 65.4% → **69.2%**，
但平均 CER 由 0.126 變差到 **0.158**；valid 88.5% → **92.3%**。
N=26 只收成功校正樣本，有選擇偏差，不能當整體準確率。

**已知限制**：`RDA-2388` 那張 Lexus 圖仍完全失敗：
真車牌的白底遮罩覆蓋率只有 3.8%，車牌面亮度 v 約 153–193。
220/180/150 三階都沒有產生足以命中的候選；這是曝光不足與顏色遮罩的硬限制。
另外，兩張定量回歸要保留：
`VF9219` 預測成 `U`（IoU 0.92，CER=1.000）、
`TU7800` 預測成 `92`（CER=1.000）。
本輪先不改 OCR，只記錄為下一輪風險。

**已重產**：`shared/stages/`（285 個 PNG）、
`shared/rectified_auto/`（26 組，`maskfill` median 0.90）。
`lpr_dev.ipynb` 已重新執行，LOC 與 EV self test 均 0 error。

## 2026-11-22 17:45 — 合併 PR #4：現場測試入口與整圖 OCR 兜底

**摘要**：合併 PR #4，新增 [INT-03] `recognize_path()` / `recognize_folder()`、
[INT-03b] 互動選圖入口，以及整圖文字候選 `detect_plate_candidates()` 和
`read_plate_wholeimage()`。定位成功走 pipeline；定位失敗或主路答案不合法時，
可再跑整圖兜底，以 `(valid, format_score, conf, length)` 擇優。

**合併前驗證**：`merge-base` 確認 master 已包含於 PR 分支、merge-tree 無衝突；
隔離工作樹執行完整 notebook，0 error。

**回歸數字**：
- LOC recall@1 51.5%、recall@k 60.6%、平均最佳 IoU 0.503
- §9 26 組 exact 69.2%、CER 0.158、valid 88.5%
- `read_plate` / 資料契約簽名未變

**口徑限制**：整圖入口是現場 demo 路徑，不應混入 §9 的 26 組上限量測。
三組報告口徑仍分開：99 張原圖 end-to-end 39.4%、95 張 stages 融合 41.1%、
26 組 rectified_auto 融合 69.2%。





