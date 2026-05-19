const http = require("http");
const fs = require("fs/promises");
const path = require("path");
const { URL } = require("url");

const port = Number(process.env.PORT || 8080);
const host = process.env.HOST || "0.0.0.0";
const logDir = path.join(__dirname, "..", "logs");
const logFile = path.join(logDir, "douyin-callback.log");

function readBody(req) {
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
    "content-type": "application/json; charset=utf-8"
  });
  res.end(JSON.stringify(data));
}

function parseBody(rawBody, contentType = "") {
  if (!rawBody) return null;
  if (contentType.includes("application/json")) {
    try {
      return JSON.parse(rawBody);
    } catch {
      return rawBody;
    }
  }
  return rawBody;
}

async function appendLog(payload) {
  await fs.mkdir(logDir, { recursive: true });
  await fs.appendFile(logFile, `${JSON.stringify(payload, null, 2)}\n\n`, "utf8");
}

const server = http.createServer(async (req, res) => {
  const requestUrl = new URL(req.url, `http://${req.headers.host || "localhost"}`);

  if (requestUrl.pathname === "/health") {
    return json(res, 200, { ok: true, service: "douyin-callback-server" });
  }

  const callbackPaths = new Set([
    "/douyin/callback",
    "/douyin/spi",
    "/douyin/webhook"
  ]);

  if (!callbackPaths.has(requestUrl.pathname)) {
    return json(res, 404, { ok: false, message: "Not found" });
  }

  try {
    const rawBody = await readBody(req);
    const payload = {
      time: new Date().toISOString(),
      method: req.method,
      path: requestUrl.pathname,
      query: Object.fromEntries(requestUrl.searchParams.entries()),
      headers: req.headers,
      body: parseBody(rawBody, req.headers["content-type"])
    };

    console.log(JSON.stringify(payload, null, 2));
    await appendLog(payload);

    return json(res, 200, {
      err_no: 0,
      err_msg: "success",
      ok: true
    });
  } catch (error) {
    console.error(error);
    return json(res, 500, {
      err_no: 500,
      err_msg: "server error",
      ok: false
    });
  }
});

server.listen(port, host, () => {
  console.log(`Douyin callback server listening on http://${host}:${port}`);
  console.log(`Health check: http://127.0.0.1:${port}/health`);
});
