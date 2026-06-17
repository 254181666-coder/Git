const path = require("node:path");
const fs = require("node:fs");
const { app, BrowserWindow, Menu, dialog, shell } = require("electron");

let mainWindow;
let serverHandle;

app.setName("木桃工具包");
Menu.setApplicationMenu(null);
app.commandLine.appendSwitch("lang", "zh-CN");
app.commandLine.appendSwitch("disable-notifications");
app.commandLine.appendSwitch("disable-accelerated-video-decode");
app.commandLine.appendSwitch("autoplay-policy", "user-gesture-required");

function writeCrashLog(message) {
  try {
    const dir = path.join(app.getPath("userData"), "logs");
    fs.mkdirSync(dir, { recursive: true });
    fs.appendFileSync(path.join(dir, "crash.log"), `[${new Date().toISOString()}] ${message}\n`);
  } catch {
    // 本地日志失败时不影响启动。
  }
}

function isHttpUrl(value) {
  try {
    const parsed = new URL(String(value || ""));
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

function isSafeAppUrl(value) {
  try {
    const parsed = new URL(String(value || ""));
    return ["http:", "https:", "about:", "data:", "blob:", "file:", "ws:", "wss:"].includes(parsed.protocol);
  } catch {
    return false;
  }
}

function lockDownWebSession(session) {
  session.setPermissionRequestHandler((_webContents, _permission, callback) => {
    callback(false);
  });
  if (typeof session.setPermissionCheckHandler === "function") {
    session.setPermissionCheckHandler(() => false);
  }
  session.webRequest.onBeforeRequest({ urls: ["<all_urls>"] }, (details, callback) => {
    callback({ cancel: !isSafeAppUrl(details.url) });
  });
}

async function createMainWindow(url) {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1080,
    minHeight: 680,
    title: "木桃工具包",
    backgroundColor: "#080d16",
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  });

  lockDownWebSession(mainWindow.webContents.session);

  mainWindow.webContents.setWindowOpenHandler(({ url: targetUrl }) => {
    if (isHttpUrl(targetUrl)) shell.openExternal(targetUrl);
    return { action: "deny" };
  });
  const blockUnsafeNavigation = (event, targetUrl) => {
    if (targetUrl && !isSafeAppUrl(targetUrl)) event.preventDefault();
  };
  mainWindow.webContents.on("will-navigate", blockUnsafeNavigation);
  mainWindow.webContents.on("will-frame-navigate", blockUnsafeNavigation);
  mainWindow.webContents.on("will-redirect", blockUnsafeNavigation);
  mainWindow.webContents.on("render-process-gone", (_event, details) => {
    writeCrashLog(`main window renderer gone: ${details?.reason || "unknown"}`);
    if (!mainWindow?.isDestroyed()) {
      setTimeout(() => {
        mainWindow.loadURL(url).catch((error) => writeCrashLog(`main reload failed: ${error.message}`));
      }, 800);
    }
  });

  await mainWindow.loadURL(url);
}

async function boot() {
  const userDataDir = app.getPath("userData");
  process.env.HKT_DATA_DIR = path.join(userDataDir, "data");
  process.env.HKT_LICENSE_SERVER_URL = process.env.HKT_LICENSE_SERVER_URL || "https://license.xyht618.cn";
  process.env.HKT_FREE_TRIAL_DAYS = process.env.HKT_FREE_TRIAL_DAYS || "3";
  process.env.HKT_AUTO_LICENSE = process.env.HKT_AUTO_LICENSE || "0";
  process.env.HKT_REQUIRE_LOGIN = process.env.HKT_REQUIRE_LOGIN || "1";
  process.env.HOST = "127.0.0.1";

  const { startServer } = require("./server");
  serverHandle = await startServer({ host: "127.0.0.1", port: 0 });
  await createMainWindow(serverHandle.url);
}

app.whenReady().then(() => {
  boot().catch((error) => {
    dialog.showErrorBox("木桃工具包启动失败", error.message || String(error));
    app.quit();
  });

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0 && serverHandle) {
      createMainWindow(serverHandle.url);
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  if (serverHandle?.server) serverHandle.server.close();
});

process.on("uncaughtException", (error) => {
  writeCrashLog(`uncaughtException: ${error?.stack || error?.message || error}`);
});

process.on("unhandledRejection", (error) => {
  writeCrashLog(`unhandledRejection: ${error?.stack || error?.message || error}`);
});
