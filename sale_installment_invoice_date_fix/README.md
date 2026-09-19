# Sale Installment Invoice Date Fix

Odoo **19.0** module for Three Corners Developments.

## What it does

When installment invoices are generated from a Sales Order (the
**Create Installment Invoices** button added by `px_custom_real_estate_management`),
this module forces every generated customer invoice to be dated correctly:

| Field | Value |
|-------|-------|
| **Invoice Date** (`invoice_date`) | the Sales Order **Order Date** (`date_order`) |
| **Due Date** (`invoice_date_due`) | the installment line **Collection Date** (`collection_date`) |

So all installments share one invoice date (the day the contract/SO was made),
while each one keeps its own future maturity date.

### Before ➜ After

```
Sales Order date: 06/09/2026

Installment 1  collection 02/09/2026
Installment 2  collection 02/12/2026
Installment 3  collection 02/03/2027

BEFORE (wrong)                         AFTER (this module)
INV1 invoice_date = 02/09/2026  X      INV1 invoice_date = 06/09/2026  due 02/09/2026
INV2 invoice_date = 02/12/2026  X      INV2 invoice_date = 06/09/2026  due 02/12/2026
INV3 invoice_date = 02/03/2027  X      INV3 invoice_date = 06/09/2026  due 02/03/2027
```

## How it works (technical)

The invoices carry `sale_order_installment_id` (-> `sale.order.installment.line`,
which holds `collection_date`) and `sale_order_id`.

1. **`account.move.create()`** (`models/account_move.py`) - the primary fix.
   For any invoice created with a `sale_order_installment_id`, it sets
   `invoice_date` = the SO `date_order` and `invoice_date_due` =
   `collection_date`, *at creation time, before the invoice is posted*.
   Because these invoices have **no payment term** (`invoice_payment_term_id`
   is empty), the explicit due date is preserved after posting.

2. **`sale.order` button overrides** (`models/sale_order.py`) -
   `action_create_installment_invoices` and
   `action_create_installment_invoices_from_so` call `super()` and then
   re-sync any invoice still in **draft** (safety net). Posted entries are
   never rewritten.

3. **Maintenance action** (`data/fix_dates_action.xml`) - a server action
   "Fix Installment Invoice Dates (draft)" that re-aligns every existing
   **draft** installment invoice in one click.

## Install

Depends on `px_custom_real_estate_management` so it always loads after it.

1. Copy the folder into your Odoo.sh addons and push, **or** zip it and use
   *Apps -> Import Module*.
2. *Apps* -> update list -> install **Sale Installment Invoice Date Fix**.

## Notes

- Only affects invoices generated from a Sales Order installment plan
  (keyed on `sale_order_installment_id`); normal invoices are untouched.
- Never modifies **posted** invoices (accounting safety). Existing wrong
  posted invoices must be fixed manually or reset to draft first.
- Does **not** change amounts, the installment schedule, or the collection
  dates - only `invoice_date`.
