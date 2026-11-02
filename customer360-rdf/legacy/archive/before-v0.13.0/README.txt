客戶360 RDF／OWL 與部門 PG v0.12.0，2026-10-22，設計草案。

最新說明：README.md；交接：HANDOFF-ZED-RDF-PG-20261022.md。
銀行新增 ETFProduct，直接繼承 fh:FinancialProduct；PG補ETF AUM／手收及底表，與基金分列且不自動合計。
ETF AUM來源DSFND.PB_FUND_MONTH，手收來源DSFND.PB_FUND_SPREAD_DAILY；AUM分類取值待確認，新欄位均pending／null且候選為空。
銀行既有 InsuranceProduct，泛指銀行通路保險，直接繼承 fh:FinancialProduct；私銀實際範圍留PG。
PG新增銀行保險AUM及日報手續費收入。AUM底表DSKPI.AFAUM_AFCUST_MON_ASSET_REPORT，保留原始投資金額意義。
保險手收底表DSINS.INSU_RPT_Q01，目前部分涵蓋；兩項月檔客戶貢獻度未併入手續費。
新AUM八欄位、手收十一欄位全部pending、table／column為null、候選為空；未建立保單／契約模型。
前批銀行海外股票、ELI、FCI、DCI純手續費已完成；DCI不含TMU損益。
目前15項AUM、14項手收有表級來源，來源接指標，不接商品分類。
金控沿用八個計算必要元素，不要求詳細公式。來源欄位、幣別、期間、識別與實際歸屬繼續待定。
清單：department-pg/METRIC-TABLE-SOURCES.md。通用手收仍是已盤來源的部分覆蓋，不直接相加。
信託／保管、開狀、利收與交易損益留待討論；權限、帳戶及畫圖暫緩。

RDF五份來源；PG六份active JSON，詳見README.md。
RDF：30 Class、6 Object Property、16 Data Property、5 Annotation Property、324 triples。
PG：36概念、462 metadata節點、972關係。RDF 19項＋PG 64項測試通過，無略過。
修改前快照：archive/before-v0.12.0/。未執行來源SQL、完整OWL推論或Neo4j部署。
outputs/rdf-review-v0.7.0 僅供歷史對照，沒有更新圖片。
