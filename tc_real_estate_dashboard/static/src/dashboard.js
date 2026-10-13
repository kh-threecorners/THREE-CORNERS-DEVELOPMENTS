/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const STATE_LABEL = { confirm: "Confirmed", draft: "Draft", proposed: "Proposed", cancel: "Cancelled" };
const STATE_CLASS = { confirm: "confirm", draft: "draft", proposed: "proposed", cancel: "cancel" };

// ---- formatting helpers ---------------------------------------------------
function fmtInt(n) { return Math.round(n || 0).toLocaleString("en-US"); }
function fmtM(n) { return ((n || 0) / 1e6).toLocaleString("en-US", { maximumFractionDigits: 1, minimumFractionDigits: 1 }); }
function shortMonth(label) {
    // "October 2026" -> "Oct 26"
    if (!label) { return ""; }
    const parts = String(label).split(" ");
    const mi = ["January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"].indexOf(parts[0]);
    const yr = parts[1] ? parts[1].slice(-2) : "";
    return (mi >= 0 ? MONTHS[mi] : parts[0]) + " " + yr;
}

export class TcReDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loading: true, error: false, v: null });
        onWillStart(async () => {
            try {
                this.state.v = await this.load();
            } catch (e) {
                this.state.error = (e && e.message) || "Failed to load dashboard data";
            } finally {
                this.state.loading = false;
            }
        });
    }

    async load() {
        const orm = this.orm;
        const today = new Date().toISOString().slice(0, 10);

        const [
            propTotal, propState, propType, propProj, propVal,
            saleTotal, saleState, confirmSums, monthlyRaw, projMoney,
            recentRaw, availRaw, dueRaw,
        ] = await Promise.all([
            orm.searchCount("property.property", []),
            orm.readGroup("property.property", [], ["id"], ["state"], { lazy: false }),
            orm.readGroup("property.property", [], ["id"], ["property_type"], { lazy: false }),
            orm.readGroup("property.property", [], ["id"], ["property_project_id"], { lazy: false }),
            orm.readGroup("property.property", [], ["unit_price:sum"], [], { lazy: false }),
            orm.searchCount("property.sale", []),
            orm.readGroup("property.sale", [], ["sale_price:sum"], ["state"], { lazy: false }),
            orm.readGroup("property.sale", [["state", "=", "confirm"]],
                ["sale_price:sum", "paid:sum", "remaining:sum", "discount_amount:sum"], [], { lazy: false }),
            orm.readGroup("property.sale", [], ["sale_price:sum"], ["order_date:month"], { lazy: false }),
            orm.readGroup("property.sale", [["state", "=", "confirm"]],
                ["sale_price:sum", "paid:sum", "remaining:sum"], ["project_id"], { lazy: false }),
            orm.searchRead("property.sale", [["property_id", "!=", false]],
                ["property_id", "partner_id", "project_id", "sale_price", "state", "order_date"],
                { limit: 6, order: "id desc" }),
            orm.searchRead("property.property", [["state", "=", "available"]],
                ["name", "property_project_id", "unit_price", "meter_price"],
                { limit: 5, order: "unit_price desc" }),
            orm.searchRead("property.sale.line",
                [["collection_status", "!=", "collected"], ["capital_repayment", ">", 0], ["collection_date", ">=", today]],
                ["name", "collection_date", "capital_repayment", "sale_id"],
                { limit: 5, order: "collection_date asc" }),
        ]);

        const countOf = (groups, key, val) => {
            const g = groups.find((x) => (Array.isArray(x[key]) ? x[key][0] : x[key]) === val);
            return g ? g.__count : 0;
        };

        const total = propTotal;
        const available = countOf(propState, "state", "available");
        const sold = countOf(propState, "state", "sold");
        const cs = (confirmSums && confirmSums[0]) || {};
        const confirmed = countOf(saleState, "state", "confirm");

        // ---- monthly series (last 12 with a date) ----
        const monthly = monthlyRaw
            .filter((g) => g["order_date:month"])
            .map((g) => ({
                label: shortMonth(g["order_date:month"]),
                value: g["sale_price"] || 0,
                count: g.__count || 0,
            }))
            .slice(-12);

        // ---- projects (units) ----
        const projUnits = propProj
            .filter((g) => g.property_project_id)
            .map((g) => ({ name: g.property_project_id[1], units: g.__count }))
            .sort((a, b) => b.units - a.units);
        const maxUnits = Math.max(1, ...projUnits.map((p) => p.units));
        projUnits.forEach((p) => { p.pct = Math.round((p.units / maxUnits) * 100); });

        // ---- bookings by status ----
        const totSale = saleState.reduce((a, b) => a + (b.__count || 0), 0) || 1;
        const statusColors = { confirm: "var(--tc-good)", draft: "var(--tc-warn)", proposed: "var(--tc-accent)", cancel: "var(--tc-danger)" };
        const status = saleState.map((g) => ({
            name: STATE_LABEL[g.state] || g.state,
            count: g.__count || 0,
            pct: Math.round(((g.__count || 0) / totSale) * 100),
            color: statusColors[g.state] || "var(--tc-accent)",
        }));

        // ---- collections by project ----
        const collproj = projMoney
            .filter((g) => g.project_id)
            .map((g) => {
                const paid = g.paid || 0, rem = g.remaining || 0, tot = paid + rem;
                return {
                    name: g.project_id[1],
                    paidM: fmtM(paid), totM: fmtM(tot),
                    pct: tot ? Math.round((paid / tot) * 100) : 0,
                };
            });

        // ---- recent bookings ----
        const recent = recentRaw.map((r) => ({
            unit: r.property_id ? r.property_id[1] : "—",
            customer: r.partner_id ? r.partner_id[1] : "—",
            project: r.project_id ? r.project_id[1] : "—",
            price: fmtInt(r.sale_price),
            state: STATE_CLASS[r.state] || "draft",
            stateLabel: STATE_LABEL[r.state] || r.state,
            date: r.order_date || "—",
        }));

        // ---- top available ----
        const units = availRaw.map((u) => ({
            unit: u.name,
            project: u.property_project_id ? u.property_project_id[1] : "—",
            price: fmtM(u.unit_price),
            meter: fmtInt(u.meter_price),
        }));

        // ---- upcoming installments ----
        const due = dueRaw.map((d) => ({
            ref: d.sale_id ? d.sale_id[1] : (d.name || "—"),
            name: d.name || "Installment",
            amount: fmtInt(d.capital_repayment),
            date: d.collection_date || "",
        }));

        // ---- monthly performance (last 6) ----
        const perf = monthly.slice(-6).map((m) => ({
            m: m.label, b: m.count,
            v: fmtM(m.value),
            avg: m.count ? fmtM(m.value / m.count) : "0.0",
        }));

        const paidTot = cs.paid || 0, remTot = cs.remaining || 0;
        const ringPct = (paidTot + remTot) ? Math.round((paidTot / (paidTot + remTot)) * 100) : 0;

        return {
            kpis: {
                total: fmtInt(total),
                available: fmtInt(available),
                availablePct: total ? Math.round((available / total) * 100) : 0,
                sold: fmtInt(sold),
                soldPct: total ? Math.round((sold / total) * 100) : 0,
                projects: projUnits.length,
                bookings: fmtInt(saleTotal),
                confirmed: fmtInt(confirmed),
                contractValue: fmtM(cs.sale_price),
                discounts: fmtM(cs.discount_amount),
                collected: fmtM(paidTot),
                remaining: fmtM(remTot),
                portfolio: fmtM((propVal && propVal[0] && propVal[0].unit_price) || 0),
            },
            chart: this.buildChart(monthly),
            projUnits, status, collproj, recent, units, due, perf,
            ring: { pct: ringPct, paid: fmtM(paidTot), remaining: fmtM(remTot) },
            asof: today,
        };
    }

    // ---- SVG chart geometry (faint bars + smooth area + line + dots) ------
    buildChart(monthly) {
        const W = 760, H = 300, pl = 44, pr = 14, pt = 18, pb = 34;
        const iw = W - pl - pr, ih = H - pt - pb;
        const n = Math.max(1, monthly.length);
        const vals = monthly.map((m) => (m.value || 0) / 1e6);
        const rawMax = Math.max(10, ...vals);
        const ymax = Math.ceil(rawMax / 25) * 25; // round up to 25s
        const step = iw / n;
        const X = (i) => pl + step * i + step / 2;
        const Y = (v) => pt + ih - (v / ymax) * ih;

        const bw = Math.min(26, step * 0.42);
        const bars = monthly.map((m, i) => {
            const y = Y(vals[i]);
            return { x: X(i) - bw / 2, y, w: bw, h: Math.max(0, pt + ih - y) };
        });

        const line = vals.map((v, i) => {
            const x = X(i), y = Y(v);
            if (i === 0) { return `M${x},${y}`; }
            const px = X(i - 1), py = Y(vals[i - 1]), cx = (px + x) / 2;
            return ` C${cx},${py} ${cx},${y} ${x},${y}`;
        }).join("");
        const area = line + ` L${X(n - 1)},${pt + ih} L${X(0)},${pt + ih} Z`;

        const dots = vals.map((v, i) => ({ x: X(i), y: Y(v) }));
        const xlabels = monthly.map((m, i) => ({ x: X(i), t: m.label }));
        const ylabels = [];
        for (let t = 0; t <= ymax; t += ymax / 4) { ylabels.push({ y: Y(t), t: Math.round(t) }); }

        // emphasise peak + last point
        let peakI = 0;
        vals.forEach((v, i) => { if (v > vals[peakI]) { peakI = i; } });
        const peak = { x: X(peakI), y: Y(vals[peakI]), t: vals[peakI].toFixed(1) };
        const last = { x: X(n - 1), y: Y(vals[n - 1]), t: vals[n - 1].toFixed(1) };

        return { W, H, bars, line, area, dots, xlabels, ylabels, peak, last };
    }

    openBookings() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Bookings",
            res_model: "property.sale",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }
}

TcReDashboard.template = "tc_real_estate_dashboard.Dashboard";
registry.category("actions").add("tc_real_estate_dashboard", TcReDashboard);
