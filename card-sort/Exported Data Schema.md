# Exported Data Schema

The card-sort tool exported one JSON file per participant. The table below summarises the exported fields.

| Section | Field | Description |
| --- | --- | --- |
| Session metadata | `schema` | Export schema version. |
| Session metadata | `sort_kind` | Sort type, recorded as `closed-hybrid`. |
| Session metadata | `exported_at` | ISO timestamp of the JSON export. |
| Session metadata | `started_at` | ISO timestamp of when the participant completed the interface tour and began sorting. |
| Session metadata | `duration_seconds` | Elapsed task time in seconds, measured from tour completion to export. |
| Session metadata | `duration_hms` | Elapsed task time in hours, minutes, and seconds. |
| Session metadata | `consent_given` | Boolean value indicating whether the participant consented before starting. |
| Study structure | `top_category_display_order` | Order in which the four top-level categories were displayed. |
| Study structure | `subcategory_suggestion_set` | Full Q01--Q14 suggestion list with labels and definitions. |
| Sort data | `top_categories` | Array of the four top-level categories. Each category contains its direct cards and subcategory instances. |
| Sort data | `direct_cards` | Cards placed directly in a top-level category without a subcategory. |
| Sort data | `subcategory_instances` | Suggested or custom subcategories created inside a top-level category. |
| Sort data | `source_chip_id` | ID of the predefined suggestion when the subcategory came from Q01--Q14. |
| Sort data | `is_custom_label` | Boolean value indicating whether the subcategory label was participant-created. |
| Sort data | `cards` | Cards placed inside the subcategory. |
| Set aside and incomplete data | `set_aside` | Cards moved to the set-aside tray, including reason and optional note. |
| Set aside and incomplete data | `unsorted` | Cards not placed at export time. |
| Set aside and incomplete data | `unsorted_display_order_at_start` | Randomised card order shown at the start of the session. |
| Participant additions | `suggested_methods` | Missing methods suggested by the participant, including title, reason, input, procedure, and output. |
