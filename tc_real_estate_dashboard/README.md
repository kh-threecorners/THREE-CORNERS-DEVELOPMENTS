# TC Real Estate Dashboard (native Odoo / OWL)

Odoo **19.0** module — a live backend dashboard for the real-estate module.
Same look as the HTML dashboard, but it lives **inside Odoo** and reads the data
**live from the ORM** every time it is opened.

## What it shows
- **KPI cards:** total / available / sold units, bookings, contract value, collected.
- **Sales growth** chart: booking value by month (last 12 months), as inline SVG.
- **Units by project** and **Bookings by status**.
- **Collections** ring (paid vs remaining) and **Collections by project**.
- **Recent bookings**, **Top available units**, **Upcoming installments**.
- **Monthly performance** table (last 6 months).

## Where the numbers come from (live)
| Widget | Model / query |
|--------|----------------|
| Units, available, sold, by project | `property.property` (`read_group` on `state`, `property_project_id`) |
| Portfolio value | `property.property` sum of `unit_price` |
| Bookings, status, contract value, discounts | `property.sale` (`read_group` on `state`) |
| Collected / remaining, by project | `property.sale` sums of `paid`, `remaining` (state = confirm) |
| Sales-growth chart, monthly performance | `property.sale` grouped by `order_date:month` |
| Recent bookings | `property.sale` (latest 6) |
| Top available units | `property.property` (state = available, top price) |
| Upcoming installments | `property.sale.line` (not collected, due ≥ today) |

Nothing is stored by this module; every figure is queried on open.

## Files
```
tc_real_estate_dashboard/
  __manifest__.py
  __init__.py
  views/dashboard_action.xml      # ir.actions.client + app menu
  static/src/dashboard.js         # OWL component (loads live data, builds chart)
  static/src/dashboard.xml        # OWL/QWeb template
  static/src/dashboard.scss        # styling (light + Odoo dark mode)
```

## Install (Odoo.sh, via git)
1. Copy the folder into the project's addons repo and push.
2. Odoo.sh rebuilds → **Apps** → Update Apps List → install **TC Real Estate Dashboard**.
3. A new top-level menu **“RE Dashboard” → Dashboard** opens the live page.

> Can't be installed through the Apps import ZIP on Odoo.sh (code modules load from
> git only) — same as the other custom modules.

## Notes / compatibility
- Depends on `px_custom_real_estate_management` (it uses that module's models/fields).
- Data access uses the OWL ORM service (`orm.readGroup`, `orm.searchRead`,
  `orm.searchCount`). If a specific 19.x build has renamed `readGroup`, switch those
  calls to `formattedReadGroup` in `dashboard.js` — the rest is unchanged.
- The menu is a standalone top-level app. To nest it inside the existing Real Estate
  app instead, set `parent=` on `menu_tc_re_dashboard` to that app's root menu id.
- The KPI card **Bookings** is clickable → opens the `property.sale` list.
- **This module has not been run on the live server yet** — review on first deploy.
