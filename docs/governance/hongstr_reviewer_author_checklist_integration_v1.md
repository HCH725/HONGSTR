# HONGSTR Reviewer-Author Checklist Integration v1

## 1. 文件目的 (Document Purpose)

這是一份 **Reviewer-Author Checklist Integration v1** 的治理說明。
其目的是讓既有的 reviewer advisory outputs，能夠「very-thin 地」 (極輕量) 掛載到 `prototype_review_pr_author_checklist_v1.md` 與 `prototype_review_reviewer_checklist_v1.md` 之中。
這不是一份創造新 review rule 的文件，而是為既有的 supplementary reviewer review 找一個合理但不具破壞性的切入點。

## 2. 為何現在做 Checklist Integration

因 HONGSTR 已導入 Reviewer Supplementation Advisory Trial (`docs/architecture/hongstr_reviewer_supplementation_advisory_trial_v1.md`)，並有相關的 manual shadow review runbook。
為了讓 PR 雙方 (Author 與 Reviewer) 在執行例行的 review checklist 時，能明確知曉這類 advisory review output 的存在與定位，故在此進行非常克制的整合。

## 3. PR Author 側應知道的 Advisory Reviewer 使用時機

- **Optional aids**: Author 應知悉，若有 Supplementary Reviewer (如 supplementary advisory outputs) 參與審查，其產生之建議或檢核結果皆為「供參」(advisory-only)。
- **Non-blocking**: 該些輔助產出不具阻斷性 (non-blocking)。
- **Checklist 體現**: Author Checklist 的前提宣告區已新增一列，明示這類 supplementary trial outputs 為可選與非阻斷性輔助。

## 4. Reviewer 側應知道的 Advisory Reviewer 限制

- **Not a final authority**: 真正的 Reviewer (人類) 應知悉，若他們參考了 supplementary reviewer 的 output 或是自動產生的摘要，這些 output 不具備最終批准權 (final review authority)。
- **Human judgment required**: Human reviewer 的最終裁斷才是真正的決策依據。
- **Checklist 體現**: Reviewer Checklist 之中已明確增加「不具有 final review authority」的限制宣告。

## 5. 與既有 Reviewer Line 文件的關係

本次整合維持並呼應了下述現有文件的精神：

- `docs/architecture/hongstr_reviewer_role_deployment_integration_v1.md`
- `docs/architecture/hongstr_reviewer_supplementation_advisory_trial_v1.md`
- `docs/architecture/hongstr_manual_shadow_review_runbook_v1.md`
以上三者共同確立了「Reviewer 必須是輔助性且無破壞性的」，此次 checklist 的薄掛載完全服膺此架構原則。

## 6. 強制紅線重申

請所有開發者與 Reviewer 正確對待此次的 checklist 補注。

- 這**不是** CI hard gate。
- 這**不是** runtime authority。
- 這**不是** final merge authority。
- Supplementary Reviewer 沒有決定 `pass/fail` 的生殺大權。
- 不可藉由擴張 checklist wording，將「參考 reviewer output」變成「mandatory hard requirement」(強制阻擋項)。

## 7. Handoff Note

後續若 Reviewer Supplementation Advisory Trial 結束或要升級為正式角色，必須另開 `upgrade review` 進行。
**不可**單獨修改此文件或前述的 checklist 即宣告升格，所有角色與權限變更必須經過完整的 Phase 1 Role Governance 流程。
