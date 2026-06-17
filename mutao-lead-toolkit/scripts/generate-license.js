#!/usr/bin/env node
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

function usage() {
  console.log([
    "用法：node scripts/generate-license.js --customer 客户名称 --expires 2026-06-30 [--plan 月度版] [--device 设备码]",
    "",
    "私钥默认读取 keys/license-private.pem，也可以用 LICENSE_PRIVATE_KEY_PATH 指定。"
  ].join("\n"));
}

function readArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!key?.startsWith("--") || value === undefined) continue;
    args[key.slice(2)] = value;
  }
  return args;
}

function base64Url(value) {
  return Buffer.from(value)
    .toString("base64")
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replaceAll("=", "");
}

const args = readArgs(process.argv.slice(2));
if (!args.customer || !args.expires || args.help) {
  usage();
  process.exit(args.help ? 0 : 1);
}

const privateKeyPath = process.env.LICENSE_PRIVATE_KEY_PATH || path.join(__dirname, "..", "keys", "license-private.pem");
const privateKey = fs.readFileSync(privateKeyPath, "utf8");
const payload = {
  licenseId: `lic_${Date.now().toString(36)}_${crypto.randomBytes(4).toString("hex")}`,
  customer: args.customer,
  plan: args.plan || "月度版",
  issuedAt: new Date().toISOString(),
  expiresAt: args.expires
};

if (args.device) payload.deviceId = args.device.trim().toUpperCase();

const payloadPart = base64Url(JSON.stringify(payload));
const signer = crypto.createSign("RSA-SHA256");
signer.update(payloadPart);
signer.end();
const signaturePart = base64Url(signer.sign(privateKey));

console.log(`${payloadPart}.${signaturePart}`);
console.error(`客户：${payload.customer}`);
console.error(`套餐：${payload.plan}`);
console.error(`到期：${payload.expiresAt}`);
console.error(`设备：${payload.deviceId || "不绑定"}`);
