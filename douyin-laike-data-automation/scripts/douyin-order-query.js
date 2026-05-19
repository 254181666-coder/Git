#!/usr/bin/env node

const fs = require("fs/promises");
const path = require("path");

const rootDir = path.resolve(__dirname, "..");
const envFile = path.join(rootDir, ".env");
const tokenCacheFile = path.join(rootDir, ".cache", "douyin-client-token.json");

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (!arg.startsWith("--")) continue;
    const key = arg.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith("--")) {
      args[key] = true;
      continue;
    }
    args[key] = next;
    index += 1;
  }
  return args;
}

async function loadEnv() {
  try {
    const content = await fs.readFile(envFile, "utf8");
    for (const rawLine of content.split(/\r?\n/)) {
      const line = rawLine.trim();
      if (!line || line.startsWith("#")) continue;
      const match = line.match(/^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/);
      if (!match) continue;
      const [, key, rawValue] = match;
      if (process.env[key]) continue;
      process.env[key] = rawValue.replace(/^["']|["']$/g, "");
    }
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
}

function requireEnv(name, fallbackName) {
  const value = process.env[name] || (fallbackName ? process.env[fallbackName] : "");
  if (!value) {
    throw new Error(`Missing ${name}${fallbackName ? ` or ${fallbackName}` : ""} in .env`);
  }
  return value;
}

function baseUrl() {
  return (process.env.DOUYIN_OPENAPI_BASE_URL || "https://open.douyin.com").replace(/\/+$/, "");
}

async function requestJson(url, options) {
  const response = await fetch(url, options);
  const text = await response.text();
  let body;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} ${response.statusText}: ${text}`);
  }
  return body;
}

async function readCachedToken() {
  try {
    const cache = JSON.parse(await fs.readFile(tokenCacheFile, "utf8"));
    if (cache.access_token && cache.expires_at && Date.now() < cache.expires_at - 5 * 60 * 1000) {
      return cache.access_token;
    }
  } catch (error) {
    if (error.code !== "ENOENT") {
      console.warn(`Ignoring token cache: ${error.message}`);
    }
  }
  return null;
}

async function writeCachedToken(accessToken, expiresIn) {
  await fs.mkdir(path.dirname(tokenCacheFile), { recursive: true });
  await fs.writeFile(
    tokenCacheFile,
    JSON.stringify(
      {
        access_token: accessToken,
        expires_at: Date.now() + Number(expiresIn || 7200) * 1000,
      },
      null,
      2
    ),
    "utf8"
  );
}

async function getClientToken({ refresh = false } = {}) {
  if (!refresh) {
    const cached = await readCachedToken();
    if (cached) return cached;
  }

  const clientKey = requireEnv("DOUYIN_APP_ID", "DOUYIN_CLIENT_KEY");
  const clientSecret = requireEnv("DOUYIN_APP_SECRET", "DOUYIN_CLIENT_SECRET");
  const body = {
    grant_type: "client_credential",
    client_key: clientKey,
    client_secret: clientSecret,
  };

  const result = await requestJson(`${baseUrl()}/oauth/client_token/`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!result || !result.data || result.data.error_code !== 0 || !result.data.access_token) {
    throw new Error(`Failed to get client_token: ${JSON.stringify(result)}`);
  }

  await writeCachedToken(result.data.access_token, result.data.expires_in);
  return result.data.access_token;
}

function toUnixSeconds(value, label) {
  if (!value) return undefined;
  if (/^\d+$/.test(value)) return value;
  const normalized = value.includes("T") ? value : value.replace(" ", "T");
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) {
    throw new Error(`Invalid ${label}: ${value}`);
  }
  return String(Math.floor(date.getTime() / 1000));
}

function buildQuery(args) {
  const accountId = args["account-id"] || process.env.DOUYIN_ACCOUNT_ID;
  if (!accountId) throw new Error("Missing --account-id or DOUYIN_ACCOUNT_ID in .env");

  const query = new URLSearchParams();
  query.set("account_id", accountId);
  query.set("page_num", args["page-num"] || "1");
  query.set("page_size", args["page-size"] || "20");

  const mappings = [
    ["order-id", "order_id"],
    ["ext-order-id", "ext_order_id"],
    ["open-id", "open_id"],
    ["order-status", "order_status"],
    ["cursor", "cursor"],
  ];
  for (const [argName, apiName] of mappings) {
    if (args[argName] !== undefined) query.set(apiName, args[argName]);
  }

  const timeMappings = [
    ["create-start", "create_order_start_time"],
    ["create-end", "create_order_end_time"],
    ["update-start", "update_order_start_time"],
    ["update-end", "update_order_end_time"],
  ];
  for (const [argName, apiName] of timeMappings) {
    const value = toUnixSeconds(args[argName], argName);
    if (value !== undefined) query.set(apiName, value);
  }

  if (args["secret-number"]) query.set("get_secret_number", "true");
  return { accountId, query };
}

async function queryOrders(args) {
  const accessToken = await getClientToken({ refresh: args["refresh-token"] });
  const { accountId, query } = buildQuery(args);
  const url = `${baseUrl()}/goodlife/v1/trade/order/query/?${query.toString()}`;

  const result = await requestJson(url, {
    method: "GET",
    headers: {
      "access-token": accessToken,
      "content-type": "application/json",
      "Rpc-Transit-Life-Account": accountId,
    },
  });
  return result;
}

function printHelp() {
  console.log(`Usage:
  npm run order:query -- --order-id 1094809189459863475
  npm run order:query -- --update-start "2026-05-18 00:00:00" --update-end "2026-05-18 23:59:59"

Options:
  --account-id <id>       Override DOUYIN_ACCOUNT_ID from .env
  --order-id <id>         Query one Douyin life service order
  --ext-order-id <id>     Query by third-party order id
  --order-status <code>   Filter by order status
  --create-start <time>   Unix seconds or "YYYY-MM-DD HH:mm:ss"
  --create-end <time>     Unix seconds or "YYYY-MM-DD HH:mm:ss"
  --update-start <time>   Unix seconds or "YYYY-MM-DD HH:mm:ss"
  --update-end <time>     Unix seconds or "YYYY-MM-DD HH:mm:ss"
  --page-num <n>          Default: 1
  --page-size <n>         Default: 20, max: 100
  --cursor <value>        Use cursor pagination
  --refresh-token         Ignore local token cache
`);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help || args.h) {
    printHelp();
    return;
  }

  await loadEnv();
  const result = await queryOrders(args);
  console.log(JSON.stringify(result, null, 2));
  const errorCode = result && result.data && Number(result.data.error_code || 0);
  if (errorCode !== 0) {
    process.exitCode = 2;
  }
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}

module.exports = {
  loadEnv,
  queryOrders,
  toUnixSeconds,
};
