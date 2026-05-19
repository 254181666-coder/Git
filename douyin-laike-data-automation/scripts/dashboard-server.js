#!/usr/bin/env node

const http = require("http");
const crypto = require("crypto");
const fs = require("fs/promises");
const path = require("path");
const { URL } = require("url");
const { loadEnv, queryOrders } = require("./douyin-order-query");

const rootDir = path.resolve(__dirname, "..");
const shopsFile = path.join(rootDir, "data", "shops.json");
const ordersFile = path.join(rootDir, "data", "orders.json");
const employeesFile = path.join(rootDir, "data", "employees.json");
const port = Number(process.env.DASHBOARD_PORT || process.env.PORT || 3010);
const host = process.env.DASHBOARD_HOST || process.env.HOST || "127.0.0.1";

const orderStatusLabels = {
  100: "待支付",
  101: "支付取消",
  200: "已支付",
  201: "待使用",
  1: "已完成",
};

const certificateStatusLabels = {
  100: "待使用",
  300: "退款中",
  301: "已退款",
  400: "履约中",
  401: "已履约",
};

function nowIso() {
  return new Date().toISOString();
}

function sanitizeId(value) {
  return String(value || "")
    .trim()
    .replace(/[^A-Za-z0-9_-]/g, "-")
    .slice(0, 80);
}

async function readJson(file, fallback) {
  try {
    return JSON.parse(await fs.readFile(file, "utf8"));
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
    return fallback;
  }
}

async function writeJson(file, data) {
  await fs.mkdir(path.dirname(file), { recursive: true });
  await fs.writeFile(file, `${JSON.stringify(data, null, 2)}\n`, "utf8");
}

async function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", (chunk) => {
      body += chunk;
      if (body.length > 1024 * 1024) {
        req.destroy();
        reject(new Error("Request body too large"));
      }
    });
    req.on("end", () => resolve(body));
    req.on("error", reject);
  });
}

function json(res, statusCode, data) {
  res.writeHead(statusCode, {
    "content-type": "application/json; charset=utf-8",
  });
  res.end(JSON.stringify(data));
}

function html(res, body) {
  res.writeHead(200, {
    "content-type": "text/html; charset=utf-8",
  });
  res.end(body);
}

function badRequest(res, message) {
  json(res, 400, { ok: false, message });
}

function secureEqual(left, right) {
  const leftBuffer = Buffer.from(String(left || ""));
  const rightBuffer = Buffer.from(String(right || ""));
  if (leftBuffer.length !== rightBuffer.length) return false;
  return crypto.timingSafeEqual(leftBuffer, rightBuffer);
}

function authConfig() {
  return {
    username: process.env.DASHBOARD_USERNAME || process.env.DASHBOARD_USER || "",
    password: process.env.DASHBOARD_PASSWORD || "",
  };
}

function isAuthorized(req) {
  const config = authConfig();
  if (!config.username || !config.password) return true;

  const header = req.headers.authorization || "";
  if (!header.startsWith("Basic ")) return false;

  let decoded = "";
  try {
    decoded = Buffer.from(header.slice(6), "base64").toString("utf8");
  } catch {
    return false;
  }

  const separator = decoded.indexOf(":");
  if (separator === -1) return false;
  const username = decoded.slice(0, separator);
  const password = decoded.slice(separator + 1);
  return secureEqual(username, config.username) && secureEqual(password, config.password);
}

function requireAuth(res) {
  res.writeHead(401, {
    "content-type": "text/plain; charset=utf-8",
    "www-authenticate": 'Basic realm="Douyin Data Dashboard", charset="UTF-8"',
  });
  res.end("Authentication required");
}

function normalizeOrder(shop, order) {
  const firstProduct = Array.isArray(order.products) ? order.products[0] || {} : {};
  const firstCertificate = Array.isArray(order.certificate) ? order.certificate[0] || {} : {};
  return {
    id: `${shop.account_id}-${order.order_id}`,
    shop_id: shop.id,
    shop_name: shop.name,
    account_id: shop.account_id,
    poi_id: order.poi_id || shop.poi_id || "",
    order_id: order.order_id,
    order_status: order.order_status,
    order_type: order.order_type,
    product_id: firstProduct.product_id || order.sku_id || "",
    product_name: firstProduct.product_name || order.sku_name || "",
    sku_id: firstProduct.sku_id || order.sku_id || "",
    sku_name: order.sku_name || firstProduct.product_name || "",
    certificate_id: firstCertificate.certificate_id || "",
    item_status: firstCertificate.item_status || "",
    pay_amount: order.pay_amount || 0,
    original_amount: order.original_amount || 0,
    receipt_amount: order.receipt_amount || 0,
    pay_time: order.pay_time || 0,
    create_order_time: order.create_order_time || 0,
    update_order_time: order.update_order_time || 0,
    raw: order,
    synced_at: nowIso(),
  };
}

function mergeOrders(existing, incoming) {
  const map = new Map(existing.map((order) => [order.id, order]));
  for (const order of incoming) {
    map.set(order.id, { ...(map.get(order.id) || {}), ...order });
  }
  return Array.from(map.values()).sort((a, b) => Number(b.pay_time || 0) - Number(a.pay_time || 0));
}

function secondsToText(seconds) {
  if (!seconds) return "";
  return new Date(Number(seconds) * 1000).toLocaleString("zh-CN", { hour12: false });
}

function moneyText(cents) {
  return (Number(cents || 0) / 100).toFixed(2);
}

function orderStatusText(value) {
  return orderStatusLabels[String(value)] || String(value || "");
}

function certificateStatusText(value) {
  return certificateStatusLabels[String(value)] || String(value || "");
}

function summarizeOrders(orders) {
  const paidOrders = orders.filter((order) => Number(order.pay_time || 0) > 0);
  const refundOrders = orders.filter((order) => String(order.item_status) === "301" || Number(order.raw?.certificate?.[0]?.refund_amount || 0) > 0);
  const completedOrders = orders.filter((order) => String(order.item_status) === "401" || String(order.order_status) === "1");
  return {
    total_orders: orders.length,
    paid_orders: paidOrders.length,
    total_pay_amount: orders.reduce((sum, order) => sum + Number(order.pay_amount || 0), 0),
    total_receipt_amount: orders.reduce((sum, order) => sum + Number(order.receipt_amount || 0), 0),
    refund_orders: refundOrders.length,
    completed_orders: completedOrders.length,
    pending_orders: orders.filter((order) => String(order.item_status) === "100" || String(order.order_status) === "201").length,
  };
}

function dashboardHtml() {
  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>抖音来客数据后台</title>
  <style>
    :root { color-scheme: light; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    * { box-sizing: border-box; }
    body { margin: 0; background: #f5f6f8; color: #20242c; }
    .shell { min-height: 100vh; display: grid; grid-template-columns: 232px minmax(0, 1fr); }
    aside { background: #fff; border-right: 1px solid #e6e8ef; padding: 18px 14px; position: sticky; top: 0; height: 100vh; }
    main { min-width: 0; }
    header { height: 64px; display: flex; align-items: center; justify-content: space-between; padding: 0 24px; background: #fff; border-bottom: 1px solid #e6e8ef; }
    h1 { font-size: 18px; margin: 0; }
    h2 { font-size: 16px; margin: 0 0 12px; }
    h3 { font-size: 14px; margin: 0 0 8px; }
    .brand { display: flex; align-items: center; gap: 10px; margin-bottom: 22px; font-weight: 700; }
    .brand-mark { width: 32px; height: 32px; border-radius: 8px; display: grid; place-items: center; background: #1f64ff; color: #fff; }
    nav { display: grid; gap: 4px; }
    nav button { width: 100%; text-align: left; background: transparent; color: #3f4654; padding: 10px 12px; }
    nav button.active { background: #eef3ff; color: #1f64ff; }
    .content { padding: 20px 24px 32px; display: grid; gap: 16px; }
    .section { display: none; }
    .section.active { display: grid; gap: 16px; }
    .grid { display: grid; grid-template-columns: 360px minmax(0, 1fr); gap: 16px; align-items: start; }
    .two { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
    .panel { background: #fff; border: 1px solid #e6e8ef; border-radius: 8px; padding: 16px; }
    .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
    .stat { background: #fff; border: 1px solid #e6e8ef; border-radius: 8px; padding: 14px; }
    .stat span { color: #646a73; font-size: 12px; }
    .stat strong { display: block; font-size: 22px; margin-top: 6px; }
    label { display: block; color: #646a73; font-size: 12px; margin: 10px 0 6px; }
    input, select, textarea { width: 100%; border: 1px solid #d9dde7; border-radius: 6px; padding: 9px 10px; font: inherit; background: #fff; }
    textarea { min-height: 70px; resize: vertical; }
    button { border: 0; border-radius: 6px; background: #1f64ff; color: #fff; padding: 9px 14px; font: inherit; cursor: pointer; white-space: nowrap; }
    button.secondary { background: #eef3ff; color: #1f64ff; }
    button.danger { background: #fff1f0; color: #c02b2b; }
    button:disabled { opacity: .6; cursor: not-allowed; }
    .row { display: flex; gap: 8px; align-items: center; }
    .row > * { flex: 1; }
    .shops { display: grid; gap: 8px; margin-top: 12px; }
    .shop { border: 1px solid #edf0f5; border-radius: 8px; padding: 10px; display: grid; gap: 6px; background: #fff; }
    .shop strong { font-size: 14px; }
    .muted { color: #646a73; font-size: 12px; }
    .pill { display: inline-block; padding: 2px 8px; border-radius: 999px; background: #eef3ff; color: #1f64ff; font-size: 12px; }
    .module-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
    .module { border: 1px solid #e6e8ef; border-radius: 8px; padding: 14px; background: #fff; min-height: 118px; }
    .module .state { margin-top: 12px; color: #646a73; font-size: 12px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 10px 8px; border-bottom: 1px solid #edf0f5; text-align: left; vertical-align: top; }
    th { color: #646a73; font-weight: 500; background: #fafbfc; }
    .toolbar { display: flex; gap: 8px; align-items: end; margin-bottom: 12px; }
    .toolbar label { margin-top: 0; }
    .status { min-height: 20px; color: #646a73; font-size: 13px; }
    .code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
    .table-scroll { overflow-x: auto; }
    .small-table td, .small-table th { white-space: nowrap; }
    .rank-list { display: grid; gap: 10px; }
    .rank-item { display: grid; gap: 6px; }
    .rank-head { display: flex; justify-content: space-between; gap: 12px; font-size: 13px; }
    .bar { height: 8px; background: #edf0f5; border-radius: 999px; overflow: hidden; }
    .bar > span { display: block; height: 100%; background: #1f64ff; border-radius: inherit; }
    .trend { display: grid; gap: 8px; }
    .trend-row { display: grid; grid-template-columns: 92px minmax(0, 1fr) 72px; gap: 10px; align-items: center; font-size: 13px; }
    .insights { display: grid; gap: 8px; }
    .insight { border: 1px solid #edf0f5; border-radius: 8px; padding: 10px; background: #fff; }
    .metric-line { display: flex; justify-content: space-between; gap: 12px; padding: 8px 0; border-bottom: 1px solid #edf0f5; font-size: 13px; }
    .metric-line:last-child { border-bottom: 0; }
    @media (max-width: 960px) {
      .shell { grid-template-columns: 1fr; }
      aside { height: auto; position: static; }
      .grid, .two, .stats, .module-grid { grid-template-columns: 1fr; }
      .toolbar { display: grid; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <aside>
      <div class="brand"><div class="brand-mark">抖</div><div>来客数据平台</div></div>
      <nav id="nav">
        <button class="active" data-section="overview">总览</button>
        <button data-section="shops">店铺管理</button>
        <button data-section="orders">订单</button>
        <button data-section="employees">职人/员工</button>
        <button data-section="products">商品/套餐</button>
        <button data-section="refunds">退款</button>
        <button data-section="billing">账单</button>
        <button data-section="sync">同步日志</button>
      </nav>
    </aside>
    <main>
      <header>
        <h1 id="pageTitle">总览</h1>
        <div class="status" id="status"></div>
      </header>
      <div class="content">
        <section class="section active" id="section-overview">
          <section class="stats" id="stats"></section>
          <section class="module-grid" id="modules"></section>
          <section class="two">
            <div class="panel">
              <h2>经营诊断</h2>
              <div class="insights" id="kpiInsights"></div>
            </div>
            <div class="panel">
              <h2>接入状态</h2>
              <div id="capabilityStatus"></div>
            </div>
          </section>
          <section class="two">
            <div class="panel">
              <h2>店铺排行</h2>
              <div class="rank-list" id="shopRanking"></div>
            </div>
            <div class="panel">
              <h2>商品排行</h2>
              <div class="rank-list" id="productRanking"></div>
            </div>
          </section>
          <section class="two">
            <div class="panel">
              <h2>日期趋势</h2>
              <div class="trend" id="dailyTrend"></div>
            </div>
            <div class="panel">
              <h2>状态分布</h2>
              <div id="statusDistribution"></div>
            </div>
          </section>
          <section class="panel">
            <h2>最近订单</h2>
            <table>
              <thead><tr><th>店铺</th><th>商品</th><th>金额</th><th>支付时间</th></tr></thead>
              <tbody id="recentOrders"></tbody>
            </table>
          </section>
        </section>

        <section class="section" id="section-shops">
          <section class="grid">
            <div class="panel">
              <h2>新增店铺</h2>
              <form id="shopForm">
                <label>店铺名称</label>
                <input name="name" required placeholder="例如 私人订制KTV(上东店)">
                <label>商户 account_id</label>
                <input name="account_id" required inputmode="numeric" placeholder="7341209399718987827">
                <label>门店 poi_id</label>
                <input name="poi_id" inputmode="numeric" placeholder="可选">
                <label>备注</label>
                <textarea name="notes" placeholder="授权状态、主体名称、联系人等"></textarea>
                <div class="row" style="margin-top:12px">
                  <button type="submit">新增店铺</button>
                  <button class="secondary" type="button" id="refreshBtn">刷新</button>
                </div>
              </form>
            </div>
            <div class="panel">
              <h2>已接入店铺</h2>
              <div class="shops" id="shops"></div>
            </div>
          </section>
        </section>

        <section class="section" id="section-orders">
          <section class="panel">
            <h2>订单采集</h2>
            <div class="toolbar">
              <div><label>店铺</label><select id="shopSelect"></select></div>
              <div><label>开始时间</label><input id="startTime" type="datetime-local"></div>
              <div><label>结束时间</label><input id="endTime" type="datetime-local"></div>
              <button id="syncBtn">拉取订单</button>
              <button class="secondary" id="exportBtn">导出 CSV</button>
            </div>
            <table>
              <thead>
                <tr><th>店铺</th><th>订单</th><th>商品/套餐</th><th>金额</th><th>状态</th><th>支付时间</th></tr>
              </thead>
              <tbody id="orders"></tbody>
            </table>
          </section>
        </section>

        <section class="section" id="section-employees">
          <section class="panel">
            <h2>职人/员工绑定</h2>
            <p class="muted">已预留数据入口，下一步接入接口：<span class="code">/goodlife/v2/craftsman_openapi/merchat/craftsman/bind_info/all/</span></p>
            <div class="toolbar">
              <div><label>店铺</label><select id="employeeShopSelect"></select></div>
              <button class="secondary" id="employeeSyncBtn">预留同步入口</button>
            </div>
            <div class="module-grid">
              <div class="module"><h3>绑定关系</h3><div class="muted">按 account_id 同步职人/员工绑定列表。</div><div class="state">接口已预留</div></div>
              <div class="module"><h3>人员分析</h3><div class="muted">后续关联员工视频、履约归属和门店贡献。</div><div class="state">数据结构已预留</div></div>
              <div class="module"><h3>权限</h3><div class="muted code">life.capacity.craftsman_openapi.merchat.craftsman.bind_info.all</div><div class="state">需确认已开通</div></div>
            </div>
            <div class="table-scroll" style="margin-top:16px">
              <table class="small-table">
                <thead><tr><th>店铺</th><th>员工/职人</th><th>抖音号</th><th>绑定类型</th><th>授权状态</th><th>更新时间</th></tr></thead>
                <tbody id="employees"></tbody>
              </table>
            </div>
          </section>
        </section>

        <section class="section" id="section-products"></section>
        <section class="section" id="section-refunds"></section>
        <section class="section" id="section-billing"></section>
        <section class="section" id="section-sync"></section>
      </div>
    </main>
  </div>
  <script>
    const state = { shops: [], orders: [], employees: [] };
    const $ = (id) => document.getElementById(id);
    const setStatus = (text) => { $("status").textContent = text || ""; };
    const money = (cents) => (Number(cents || 0) / 100).toFixed(2);
    const time = (seconds) => seconds ? new Date(Number(seconds) * 1000).toLocaleString("zh-CN", { hour12: false }) : "";
    const dateKey = (seconds) => seconds ? new Date(Number(seconds) * 1000).toISOString().slice(0, 10) : "未支付";
    const percent = (value, total) => total ? (Number(value || 0) / Number(total) * 100).toFixed(1) + "%" : "0.0%";
    const orderStatusText = (value) => ({ "100": "待支付", "101": "支付取消", "200": "已支付", "201": "待使用", "1": "已完成" }[String(value)] || value || "-");
    const itemStatusText = (value) => ({ "100": "待使用", "300": "退款中", "301": "已退款", "400": "履约中", "401": "已履约" }[String(value)] || value || "-");
    const basePath = window.location.pathname.endsWith("/") ? window.location.pathname : window.location.pathname + "/";
    const apiPath = (path) => new URL(path.replace(/^\\//, ""), window.location.origin + basePath).pathname;

    async function api(path, options = {}) {
      const response = await fetch(apiPath(path), {
        headers: { "content-type": "application/json" },
        ...options,
      });
      const data = await response.json();
      if (!response.ok || data.ok === false) throw new Error(data.message || "请求失败");
      return data;
    }

    function isPaid(order) {
      return Number(order.pay_time || 0) > 0 || Number(order.pay_amount || 0) > 0;
    }

    function isRefund(order) {
      return String(order.item_status) === "301" || Number(order.raw?.certificate?.[0]?.refund_amount || 0) > 0;
    }

    function isFulfilled(order) {
      return String(order.item_status) === "401" || String(order.order_status) === "1";
    }

    function isPendingUse(order) {
      return String(order.item_status) === "100" || String(order.order_status) === "201" || String(order.item_status) === "400";
    }

    function addMetric(map, key, label, order) {
      const item = map.get(key) || { key, label, orders: 0, paid_orders: 0, pay_amount: 0, receipt_amount: 0, refund_orders: 0, fulfilled_orders: 0, pending_orders: 0 };
      item.orders += 1;
      if (isPaid(order)) item.paid_orders += 1;
      if (isRefund(order)) item.refund_orders += 1;
      if (isFulfilled(order)) item.fulfilled_orders += 1;
      if (isPendingUse(order)) item.pending_orders += 1;
      item.pay_amount += Number(order.pay_amount || 0);
      item.receipt_amount += Number(order.receipt_amount || 0);
      map.set(key, item);
    }

    function analytics() {
      const totals = { orders: 0, paid_orders: 0, pay_amount: 0, receipt_amount: 0, refund_orders: 0, fulfilled_orders: 0, pending_orders: 0 };
      const byShop = new Map();
      const byProduct = new Map();
      const byDay = new Map();
      const byStatus = new Map();
      for (const order of state.orders) {
        addMetric(byShop, order.shop_id || order.account_id || "unknown", order.shop_name || "未知店铺", order);
        addMetric(byProduct, order.product_id || order.sku_id || "unknown", order.product_name || order.sku_name || "未知商品", order);
        addMetric(byDay, dateKey(order.pay_time || order.create_order_time), dateKey(order.pay_time || order.create_order_time), order);
        const status = itemStatusText(order.item_status) !== "-" ? itemStatusText(order.item_status) : orderStatusText(order.order_status);
        addMetric(byStatus, status, status, order);
        totals.orders += 1;
        if (isPaid(order)) totals.paid_orders += 1;
        if (isRefund(order)) totals.refund_orders += 1;
        if (isFulfilled(order)) totals.fulfilled_orders += 1;
        if (isPendingUse(order)) totals.pending_orders += 1;
        totals.pay_amount += Number(order.pay_amount || 0);
        totals.receipt_amount += Number(order.receipt_amount || 0);
      }
      return {
        totals,
        shops: Array.from(byShop.values()).sort((a, b) => b.pay_amount - a.pay_amount),
        products: Array.from(byProduct.values()).sort((a, b) => b.pay_amount - a.pay_amount),
        days: Array.from(byDay.values()).sort((a, b) => String(a.key).localeCompare(String(b.key))),
        statuses: Array.from(byStatus.values()).sort((a, b) => b.orders - a.orders),
      };
    }

    function rankHtml(items, valueKey = "pay_amount") {
      if (!items.length) return '<div class="muted">暂无数据</div>';
      const max = Math.max(...items.map((item) => Number(item[valueKey] || 0)), 1);
      return items.slice(0, 8).map((item) => {
        const width = Math.max(3, Number(item[valueKey] || 0) / max * 100);
        return '<div class="rank-item"><div class="rank-head"><strong>' + item.label + '</strong><span>¥' + money(item.pay_amount) + ' / ' + item.orders + '单</span></div><div class="bar"><span style="width:' + width + '%"></span></div><div class="muted">客单 ¥' + money(item.orders ? item.pay_amount / item.orders : 0) + '，退款率 ' + percent(item.refund_orders, item.orders) + '</div></div>';
      }).join("");
    }

    function renderAnalytics() {
      const data = analytics();
      const totals = data.totals;
      const avgOrder = totals.orders ? totals.pay_amount / totals.orders : 0;
      const maxDay = Math.max(...data.days.map((item) => item.pay_amount), 1);
      $("kpiInsights").innerHTML = [
        ["客单价", "¥" + money(avgOrder), "按当前已采集订单计算"],
        ["核销/履约率", percent(totals.fulfilled_orders, totals.orders), totals.fulfilled_orders + " / " + totals.orders + " 单"],
        ["退款率", percent(totals.refund_orders, totals.orders), totals.refund_orders + " / " + totals.orders + " 单"],
        ["待使用/履约中", totals.pending_orders + " 单", totals.pending_orders ? "需要持续跟踪核销与退款变化" : "暂无待处理订单"],
      ].map((item) => '<div class="insight"><div class="metric-line"><strong>' + item[0] + '</strong><span>' + item[1] + '</span></div><div class="muted">' + item[2] + '</div></div>').join("");
      $("shopRanking").innerHTML = rankHtml(data.shops);
      $("productRanking").innerHTML = rankHtml(data.products);
      $("dailyTrend").innerHTML = data.days.length ? data.days.map((item) => {
        const width = Math.max(3, item.pay_amount / maxDay * 100);
        return '<div class="trend-row"><span class="code">' + item.label + '</span><div class="bar"><span style="width:' + width + '%"></span></div><strong>¥' + money(item.pay_amount) + '</strong></div>';
      }).join("") : '<div class="muted">暂无数据</div>';
      $("statusDistribution").innerHTML = data.statuses.length ? data.statuses.map((item) => '<div class="metric-line"><span>' + item.label + '</span><strong>' + item.orders + ' 单 · ' + percent(item.orders, totals.orders) + '</strong></div>').join("") : '<div class="muted">暂无数据</div>';
    }

    function renderStats() {
      const total = state.orders.length;
      const amount = state.orders.reduce((sum, order) => sum + Number(order.pay_amount || 0), 0);
      const receipt = state.orders.reduce((sum, order) => sum + Number(order.receipt_amount || 0), 0);
      const pending = state.orders.filter((order) => String(order.item_status) === "100" || String(order.order_status) === "201").length;
      const refunds = state.orders.filter((order) => String(order.item_status) === "301").length;
      const shops = state.shops.length;
      $("stats").innerHTML = [
        ["店铺数", shops],
        ["订单数", total],
        ["支付金额", "¥" + money(amount)],
        ["商家应收", "¥" + money(receipt)],
        ["待使用", pending],
        ["已退款", refunds],
      ].map(([label, value]) => '<div class="stat"><span>' + label + '</span><strong>' + value + '</strong></div>').join("");
    }

    function renderModules() {
      const modules = [
        ["订单", "已验证", "订单明细、金额、商品和状态"],
        ["职人/员工", "下一步", "员工/职人绑定关系与人员分析"],
        ["商品/套餐", "已验证", "线上商品、SKU、价格和适用门店"],
        ["券与核销", "已验证", "验券历史、券码、核销时间和金额"],
        ["退款", "可访问", "接口已通，待真实退款数据补齐字段"],
        ["账单", "已验证", "分账、服务费、商家应收和账单明细"]
      ];
      $("modules").innerHTML = modules.map((item) => '<div class="module"><h3>' + item[0] + '</h3><span class="pill">' + item[1] + '</span><div class="state">' + item[2] + '</div></div>').join("");
      $("capabilityStatus").innerHTML = [
        "订单查询：已验证",
        "佳木斯：订单、核销、商品、账单已验证",
        "服务器 IP 白名单：已配置 47.94.244.186",
        "多店接入：逐店确认精确 account_id",
        "商品/套餐：官方接口已可读取",
        "职人/员工：待接入 connector"
      ].map((text) => '<div class="shop"><strong>' + text + '</strong></div>').join("");
    }

    function renderShops() {
      $("shops").innerHTML = state.shops.map((shop) => \`
        <div class="shop">
          <strong>\${shop.name}</strong>
          <div class="muted code">account_id: \${shop.account_id}</div>
          <div class="muted code">poi_id: \${shop.poi_id || "-"}</div>
          <div class="muted">\${shop.notes || ""}</div>
          <div class="row">
            <button class="secondary" onclick="selectShop('\${shop.id}')">选择</button>
            <button class="danger" onclick="deleteShop('\${shop.id}')">删除</button>
          </div>
        </div>
      \`).join("");
      $("shopSelect").innerHTML = state.shops.map((shop) => \`<option value="\${shop.id}">\${shop.name}</option>\`).join("");
      $("employeeShopSelect").innerHTML = state.shops.map((shop) => \`<option value="\${shop.id}">\${shop.name}</option>\`).join("");
    }

    function renderOrders() {
      $("orders").innerHTML = state.orders.map((order) => \`
        <tr>
          <td>\${order.shop_name}<div class="muted code">\${order.account_id}</div></td>
          <td class="code">\${order.order_id}<div class="muted">券: \${order.certificate_id || "-"}</div></td>
          <td>\${order.product_name || order.sku_name || "-"}<div class="muted code">\${order.product_id || ""}</div></td>
          <td>¥\${money(order.pay_amount)}<div class="muted">原价 ¥\${money(order.original_amount)}</div></td>
          <td>\${orderStatusText(order.order_status)}<div class="muted">券: \${itemStatusText(order.item_status)}</div></td>
          <td>\${time(order.pay_time)}</td>
        </tr>
      \`).join("");
      $("recentOrders").innerHTML = state.orders.slice(0, 8).map((order) => \`
        <tr>
          <td>\${order.shop_name}</td>
          <td>\${order.product_name || order.sku_name || "-"}</td>
          <td>¥\${money(order.pay_amount)}</td>
          <td>\${time(order.pay_time)}</td>
        </tr>
      \`).join("");
    }

    function renderEmployees() {
      $("employees").innerHTML = state.employees.length ? state.employees.map((item) => \`
        <tr>
          <td>\${item.shop_name || "-"}</td>
          <td>\${item.name || item.craftsman_name || "-"}</td>
          <td class="code">\${item.douyin_id || item.open_id || item.uid || "-"}</td>
          <td>\${item.bind_type || item.role || "-"}</td>
          <td>\${item.auth_status || item.status || "待同步"}</td>
          <td>\${item.updated_at ? new Date(item.updated_at).toLocaleString("zh-CN", { hour12: false }) : "-"}</td>
        </tr>
      \`).join("") : '<tr><td colspan="6" class="muted">员工/职人数据入口已预留，待开通能力并接入同步 connector。</td></tr>';
    }

    function render() {
      renderStats();
      renderModules();
      renderShops();
      renderOrders();
      renderEmployees();
      renderAnalytics();
      renderPlaceholderSections();
    }

    function renderPlaceholderSections() {
      const placeholders = {
        refunds: ["退款", "退款单、退款金额、退款时间和原订单关联会放在这里。"],
        billing: ["账单", "结算金额、手续费、账单明细和财务对账会放在这里。"],
        sync: ["同步日志", "每次采集的时间、店铺、结果和错误信息会放在这里。"]
      };
      for (const key of Object.keys(placeholders)) {
        const target = $("section-" + key);
        if (!target || target.dataset.ready) continue;
        target.dataset.ready = "1";
        target.innerHTML = '<section class="panel"><h2>' + placeholders[key][0] + '</h2><p class="muted">' + placeholders[key][1] + '</p><div class="module-grid"><div class="module"><h3>数据接入</h3><span class="pill">待接入</span><div class="state">新增 connector 后在此同步</div></div><div class="module"><h3>分析看板</h3><span class="pill">规划中</span><div class="state">按店铺、时间、状态聚合</div></div><div class="module"><h3>导出</h3><span class="pill">规划中</span><div class="state">CSV / Excel</div></div></div></section>';
      }
      renderProductsSection();
    }

    function productRows() {
      const map = new Map();
      for (const order of state.orders) {
        const key = order.product_id || order.sku_id || order.product_name || "unknown";
        const current = map.get(key) || {
          product_id: order.product_id || "",
          sku_id: order.sku_id || "",
          product_name: order.product_name || order.sku_name || "",
          shops: new Set(),
          orders: 0,
          pay_amount: 0,
          refund_orders: 0,
        };
        current.shops.add(order.shop_name);
        current.orders += 1;
        current.pay_amount += Number(order.pay_amount || 0);
        if (String(order.item_status) === "301") current.refund_orders += 1;
        map.set(key, current);
      }
      return Array.from(map.values()).map((item) => ({ ...item, shops: Array.from(item.shops).join("、") }))
        .sort((a, b) => b.pay_amount - a.pay_amount);
    }

    function renderProductsSection() {
      const target = $("section-products");
      if (!target) return;
      const rows = productRows();
      target.innerHTML = \`
        <section class="panel">
          <h2>商品/套餐</h2>
          <p class="muted">当前先根据订单自动汇总 product_id / sku_id。你拿到新的商品 ID 后，可以先在店铺备注里记录，下一步我会把这里做成可编辑商品档案。</p>
          <div class="table-scroll">
            <table class="small-table">
              <thead><tr><th>商品/套餐</th><th>product_id</th><th>sku_id</th><th>关联店铺</th><th>订单数</th><th>支付金额</th><th>退款单</th></tr></thead>
              <tbody>\${rows.map((item) => \`
                <tr>
                  <td>\${item.product_name || "-"}</td>
                  <td class="code">\${item.product_id || "-"}</td>
                  <td class="code">\${item.sku_id || "-"}</td>
                  <td>\${item.shops || "-"}</td>
                  <td>\${item.orders}</td>
                  <td>¥\${money(item.pay_amount)}</td>
                  <td>\${item.refund_orders}</td>
                </tr>
              \`).join("")}</tbody>
            </table>
          </div>
        </section>\`;
    }

    async function loadAll() {
      setStatus("加载中...");
      const [shops, orders, employees] = await Promise.all([api("api/shops"), api("api/orders"), api("api/employees")]);
      state.shops = shops.shops;
      state.orders = orders.orders;
      state.employees = employees.employees;
      render();
      setStatus("就绪");
    }

    async function deleteShop(id) {
      if (!confirm("确认删除这个店铺配置？已采集订单不会删除。")) return;
      await api("api/shops/" + encodeURIComponent(id), { method: "DELETE" });
      await loadAll();
    }

    function selectShop(id) {
      $("shopSelect").value = id;
    }

    function localDateTimeToText(value) {
      return value ? value.replace("T", " ") + ":00" : "";
    }

    $("shopForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      const payload = Object.fromEntries(form.entries());
      setStatus("保存店铺...");
      await api("api/shops", { method: "POST", body: JSON.stringify(payload) });
      event.currentTarget.reset();
      await loadAll();
    });

    $("refreshBtn").addEventListener("click", loadAll);

    $("syncBtn").addEventListener("click", async () => {
      const shopId = $("shopSelect").value;
      if (!shopId) return setStatus("请先新增或选择店铺");
      const payload = {
        update_start: localDateTimeToText($("startTime").value),
        update_end: localDateTimeToText($("endTime").value),
      };
      setStatus("正在拉取订单...");
      const result = await api("api/shops/" + encodeURIComponent(shopId) + "/sync", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      state.orders = result.orders;
      render();
      setStatus("本次新增/更新 " + result.synced + " 笔订单");
    });

    $("employeeSyncBtn").addEventListener("click", async () => {
      const shopId = $("employeeShopSelect").value;
      if (!shopId) return setStatus("请先新增或选择店铺");
      try {
        await api("api/shops/" + encodeURIComponent(shopId) + "/employees/sync", { method: "POST" });
      } catch (error) {
        setStatus(error.message);
      }
    });

    $("exportBtn").addEventListener("click", () => {
      window.location.href = apiPath("api/orders.csv");
    });

    $("nav").addEventListener("click", (event) => {
      const button = event.target.closest("button[data-section]");
      if (!button) return;
      document.querySelectorAll("nav button").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".section").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      $("section-" + button.dataset.section).classList.add("active");
      $("pageTitle").textContent = button.textContent;
    });

    loadAll().catch((error) => setStatus(error.message));
  </script>
</body>
</html>`;
}

function csvEscape(value) {
  const text = String(value == null ? "" : value);
  if (/[",\n]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

function ordersCsv(orders) {
  const headers = ["店铺", "account_id", "订单ID", "商品ID", "SKU ID", "商品名称", "券ID", "订单状态", "券状态", "支付金额", "商家应收", "支付时间"];
  const rows = orders.map((order) => [
    order.shop_name,
    order.account_id,
    order.order_id,
    order.product_id,
    order.sku_id,
    order.product_name,
    order.certificate_id,
    orderStatusText(order.order_status),
    certificateStatusText(order.item_status),
    moneyText(order.pay_amount),
    moneyText(order.receipt_amount),
    secondsToText(order.pay_time),
  ]);
  return [headers, ...rows].map((row) => row.map(csvEscape).join(",")).join("\n");
}

function productsFromOrders(orders) {
  const map = new Map();
  for (const order of orders) {
    const key = order.product_id || order.sku_id || order.product_name || "unknown";
    const existing = map.get(key) || {
      product_id: order.product_id || "",
      sku_id: order.sku_id || "",
      product_name: order.product_name || order.sku_name || "",
      shops: [],
      order_count: 0,
      pay_amount: 0,
      receipt_amount: 0,
      refund_order_count: 0,
    };
    if (order.shop_name && !existing.shops.includes(order.shop_name)) existing.shops.push(order.shop_name);
    existing.order_count += 1;
    existing.pay_amount += Number(order.pay_amount || 0);
    existing.receipt_amount += Number(order.receipt_amount || 0);
    if (String(order.item_status) === "301") existing.refund_order_count += 1;
    map.set(key, existing);
  }
  return Array.from(map.values()).sort((a, b) => b.pay_amount - a.pay_amount);
}

async function handleApi(req, res, requestUrl) {
  if (req.method === "GET" && requestUrl.pathname === "/api/shops") {
    const shops = await readJson(shopsFile, []);
    return json(res, 200, { ok: true, shops });
  }

  if (req.method === "POST" && requestUrl.pathname === "/api/shops") {
    const body = JSON.parse((await readBody(req)) || "{}");
    if (!body.name || !body.account_id) return badRequest(res, "店铺名称和 account_id 必填");
    const shops = await readJson(shopsFile, []);
    if (shops.some((shop) => shop.account_id === String(body.account_id).trim())) {
      return badRequest(res, "这个 account_id 已存在");
    }
    const shop = {
      id: `shop-${sanitizeId(body.account_id)}`,
      name: String(body.name).trim(),
      account_id: String(body.account_id).trim(),
      poi_id: String(body.poi_id || "").trim(),
      status: "active",
      notes: String(body.notes || "").trim(),
      created_at: nowIso(),
      updated_at: nowIso(),
    };
    shops.push(shop);
    await writeJson(shopsFile, shops);
    return json(res, 201, { ok: true, shop });
  }

  const deleteMatch = requestUrl.pathname.match(/^\/api\/shops\/([^/]+)$/);
  if (req.method === "DELETE" && deleteMatch) {
    const shopId = decodeURIComponent(deleteMatch[1]);
    const shops = await readJson(shopsFile, []);
    await writeJson(shopsFile, shops.filter((shop) => shop.id !== shopId));
    return json(res, 200, { ok: true });
  }

  const syncMatch = requestUrl.pathname.match(/^\/api\/shops\/([^/]+)\/sync$/);
  if (req.method === "POST" && syncMatch) {
    const shopId = decodeURIComponent(syncMatch[1]);
    const shops = await readJson(shopsFile, []);
    const shop = shops.find((item) => item.id === shopId);
    if (!shop) return badRequest(res, "店铺不存在");
    const body = JSON.parse((await readBody(req)) || "{}");
    const queryArgs = {
      "account-id": shop.account_id,
      "page-size": "100",
    };
    if (body.update_start) queryArgs["update-start"] = body.update_start;
    if (body.update_end) queryArgs["update-end"] = body.update_end;
    const result = await queryOrders(queryArgs);
    const errorCode = result && result.data && Number(result.data.error_code || 0);
    if (errorCode !== 0) {
      return json(res, 502, { ok: false, message: result.data.description || "订单查询失败", result });
    }
    const remoteOrders = Array.isArray(result.data.orders) ? result.data.orders : [];
    const normalized = remoteOrders.map((order) => normalizeOrder(shop, order));
    const existing = await readJson(ordersFile, []);
    const merged = mergeOrders(existing, normalized);
    await writeJson(ordersFile, merged);
    return json(res, 200, { ok: true, synced: normalized.length, orders: merged, raw: result });
  }

  if (req.method === "GET" && requestUrl.pathname === "/api/orders") {
    const orders = await readJson(ordersFile, []);
    return json(res, 200, { ok: true, summary: summarizeOrders(orders), orders });
  }

  if (req.method === "GET" && requestUrl.pathname === "/api/products") {
    const orders = await readJson(ordersFile, []);
    return json(res, 200, { ok: true, products: productsFromOrders(orders) });
  }

  if (req.method === "GET" && requestUrl.pathname === "/api/employees") {
    const employees = await readJson(employeesFile, []);
    return json(res, 200, { ok: true, employees });
  }

  const employeeSyncMatch = requestUrl.pathname.match(/^\/api\/shops\/([^/]+)\/employees\/sync$/);
  if (req.method === "POST" && employeeSyncMatch) {
    const shopId = decodeURIComponent(employeeSyncMatch[1]);
    const shops = await readJson(shopsFile, []);
    const shop = shops.find((item) => item.id === shopId);
    if (!shop) return badRequest(res, "店铺不存在");
    return json(res, 501, {
      ok: false,
      message: "员工/职人同步入口已预留，待开通 life.capacity.craftsman_openapi.merchat.craftsman.bind_info.all 并接入 connector",
      required_capability: "life.capacity.craftsman_openapi.merchat.craftsman.bind_info.all",
      planned_endpoint: "/goodlife/v2/craftsman_openapi/merchat/craftsman/bind_info/all/",
      shop,
    });
  }

  if (req.method === "GET" && requestUrl.pathname === "/api/orders.csv") {
    const orders = await readJson(ordersFile, []);
    res.writeHead(200, {
      "content-type": "text/csv; charset=utf-8",
      "content-disposition": 'attachment; filename="douyin-orders.csv"',
    });
    return res.end(`\ufeff${ordersCsv(orders)}`);
  }

  return json(res, 404, { ok: false, message: "Not found" });
}

async function start() {
  await loadEnv();
  if (!authConfig().username || !authConfig().password) {
    console.warn("Dashboard auth is disabled. Set DASHBOARD_USERNAME and DASHBOARD_PASSWORD in .env before exposing this service.");
  }
  const server = http.createServer(async (req, res) => {
    const requestUrl = new URL(req.url, `http://${req.headers.host || "localhost"}`);
    try {
      if (!isAuthorized(req)) return requireAuth(res);
      if (requestUrl.pathname === "/") return html(res, dashboardHtml());
      if (requestUrl.pathname.startsWith("/api/")) return handleApi(req, res, requestUrl);
      return json(res, 404, { ok: false, message: "Not found" });
    } catch (error) {
      console.error(error);
      return json(res, 500, { ok: false, message: error.message });
    }
  });
  server.listen(port, host, () => {
    console.log(`Douyin dashboard listening on http://${host}:${port}`);
  });
}

start().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
