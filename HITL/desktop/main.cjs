const { app, BrowserWindow, dialog, shell } = require("electron");
const { spawn } = require("child_process");
const fs = require("fs");
const http = require("http");
const net = require("net");
const path = require("path");

const DEFAULT_HOST = "127.0.0.1";
const DEFAULT_PORT = 8765;
const DEFAULT_OLLAMA_PORT = 11434;
const HEALTH_TIMEOUT_MS = 30000;
const DEFAULT_MODEL = "llama3:8b";

let mainWindow = null;
let backendProcess = null;
let backendPort = null;
let backendLogStream = null;

function appRootPath(...segments) {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, ...segments);
  }
  return path.join(__dirname, "..", "..", ...segments);
}

function hitlPath(...segments) {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "HITL", ...segments);
  }
  return path.join(__dirname, "..", ...segments);
}

function runtimeAssetPath(...segments) {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, ...segments);
  }
  return path.join(__dirname, "runtime-assets", ...segments);
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
  return dirPath;
}

function ensureExecutable(filePath) {
  if (process.platform !== "win32" && fs.existsSync(filePath)) {
    fs.chmodSync(filePath, 0o755);
  }
  return filePath;
}

function directoryHasContent(dirPath) {
  try {
    return fs.existsSync(dirPath) && fs.readdirSync(dirPath).some((entry) => entry !== ".gitkeep");
  } catch {
    return false;
  }
}

function copyMissingTree(sourceDir, targetDir) {
  if (!directoryHasContent(sourceDir)) {
    return false;
  }

  ensureDir(targetDir);
  for (const entry of fs.readdirSync(sourceDir, { withFileTypes: true })) {
    if (entry.name === ".gitkeep") {
      continue;
    }

    const sourcePath = path.join(sourceDir, entry.name);
    const targetPath = path.join(targetDir, entry.name);
    if (entry.isDirectory()) {
      copyMissingTree(sourcePath, targetPath);
      continue;
    }
    if (!entry.isFile()) {
      continue;
    }

    const sourceStat = fs.statSync(sourcePath);
    const targetExists = fs.existsSync(targetPath);
    const targetMatches = targetExists && fs.statSync(targetPath).size === sourceStat.size;
    if (!targetMatches) {
      ensureDir(path.dirname(targetPath));
      fs.copyFileSync(sourcePath, targetPath);
    }
  }
  return true;
}

function findPythonCommand() {
  if (process.env.HITL_PYTHON) {
    return process.env.HITL_PYTHON;
  }

  const bundledPython =
    process.platform === "win32"
      ? appRootPath("python", "python.exe")
      : appRootPath("python", "bin", "python3");

  if (fs.existsSync(bundledPython)) {
    return bundledPython;
  }

  return process.platform === "win32" ? "python" : "python3";
}

function backendExecutableName() {
  return process.platform === "win32" ? "hitl-api.exe" : "hitl-api";
}

function platformAssetKey() {
  const arch = process.arch === "arm64" ? "arm64" : "x64";
  return `${process.platform}-${arch}`;
}

function bundledExecutableCandidates(folderName, executableName) {
  const key = platformAssetKey();
  return [
    runtimeAssetPath(folderName, key, executableName),
    runtimeAssetPath(folderName, executableName),
  ];
}

function backendExecutableCandidates() {
  const explicitBackend = process.env.HITL_BACKEND_EXECUTABLE;
  return [
    explicitBackend,
    app.isPackaged
      ? appRootPath("backend", "hitl-api", backendExecutableName())
      : path.join(__dirname, "backend-dist", "hitl-api", backendExecutableName()),
  ].filter(Boolean);
}

function findBackendExecutable() {
  return backendExecutableCandidates().find((candidate) => fs.existsSync(candidate));
}

function findBundledJavaHome() {
  const explicitJavaHome = process.env.HITL_JAVA_HOME;
  const key = platformAssetKey();
  return [
    explicitJavaHome,
    runtimeAssetPath("jre", key),
    runtimeAssetPath("jre"),
  ].filter(Boolean).find((candidate) => fs.existsSync(path.join(candidate, "bin", process.platform === "win32" ? "java.exe" : "java")));
}

function findOllamaCommand() {
  if (process.env.HITL_OLLAMA_COMMAND) {
    return process.env.HITL_OLLAMA_COMMAND;
  }

  const executableName = process.platform === "win32" ? "ollama.exe" : "ollama";
  const bundledOllama = bundledExecutableCandidates("ollama", executableName)
    .find((candidate) => fs.existsSync(candidate));
  return bundledOllama ? ensureExecutable(bundledOllama) : "ollama";
}

function provisionBundledOllamaModels(targetModelsDir) {
  const bundledModelsDir = runtimeAssetPath("ollama-models");
  return copyMissingTree(bundledModelsDir, targetModelsDir);
}

function findFreePort(preferredPort) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.unref();
    server.once("error", () => resolve(findFreePort(0)));
    server.listen({ host: DEFAULT_HOST, port: preferredPort }, () => {
      const address = server.address();
      server.close(() => resolve(address.port));
    });
  });
}

function requestJson(url, options = {}) {
  return new Promise((resolve, reject) => {
    const request = http.request(url, options, (response) => {
      let body = "";
      response.setEncoding("utf8");
      response.on("data", (chunk) => {
        body += chunk;
      });
      response.on("end", () => {
        try {
          resolve(JSON.parse(body || "{}"));
        } catch (error) {
          reject(error);
        }
      });
    });
    request.setTimeout(3000, () => request.destroy(new Error("Request timed out")));
    request.on("error", reject);
    request.end();
  });
}

async function waitForHealth(port) {
  const healthUrl = `http://${DEFAULT_HOST}:${port}/health`;
  const startedAt = Date.now();
  let lastError = null;

  while (Date.now() - startedAt < HEALTH_TIMEOUT_MS) {
    try {
      const response = await requestJson(healthUrl);
      if (response.status === "ok") {
        return;
      }
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 400));
  }

  throw lastError || new Error("HITL backend did not become ready.");
}

async function startBackend() {
  const userDataDir = app.getPath("userData");
  const runtimeDir = ensureDir(path.join(userDataDir, "runtime"));
  const uploadDir = ensureDir(path.join(runtimeDir, "uploads"));
  const outputDir = ensureDir(path.join(runtimeDir, "outputs"));
  const ollamaModelsDir = ensureDir(path.join(userDataDir, "models", "ollama"));
  const logDir = ensureDir(path.join(userDataDir, "logs"));
  const serverScript = hitlPath("local_api_server.py");
  const sampleWorkbook = hitlPath("Essays.xlsx");
  const bundledBackend = findBackendExecutable();
  const bundledJavaHome = findBundledJavaHome();
  const ollamaCommand = findOllamaCommand();
  const modelName = process.env.HITL_MODEL || DEFAULT_MODEL;
  const copiedBundledModels = provisionBundledOllamaModels(ollamaModelsDir);

  backendPort = await findFreePort(DEFAULT_PORT);
  const ollamaPort = await findFreePort(DEFAULT_OLLAMA_PORT);
  const ollamaUrl = process.env.HITL_OLLAMA_URL || `http://${DEFAULT_HOST}:${ollamaPort}/api/chat`;
  const backendArgs = [
    "--host",
    DEFAULT_HOST,
    "--port",
    String(backendPort),
    "--upload-dir",
    uploadDir,
    "--output-dir",
    outputDir,
    "--sample-workbook",
    sampleWorkbook,
    "--model",
    modelName,
    "--ollama-url",
    ollamaUrl,
    "--ollama-command",
    ollamaCommand,
    "--ollama-models-dir",
    ollamaModelsDir,
  ];
  const backendCommand = bundledBackend || findPythonCommand();
  const launchArgs = bundledBackend ? backendArgs : [serverScript, ...backendArgs];
  const launchCwd = bundledBackend ? path.dirname(bundledBackend) : appRootPath();
  const backendEnv = {
    ...process.env,
    OLLAMA_MODELS: process.env.OLLAMA_MODELS || ollamaModelsDir,
    OLLAMA_HOST: process.env.OLLAMA_HOST || `${DEFAULT_HOST}:${ollamaPort}`,
    PYTHONUNBUFFERED: "1",
  };

  if (bundledJavaHome) {
    backendEnv.JAVA_HOME = bundledJavaHome;
    backendEnv.PATH = `${path.join(bundledJavaHome, "bin")}${path.delimiter}${backendEnv.PATH || ""}`;
  }

  backendLogStream = fs.createWriteStream(path.join(logDir, "hitl-backend.log"), { flags: "a" });
  backendLogStream.write(`\n[${new Date().toISOString()}] Starting HITL backend on ${backendPort}\n`);
  backendLogStream.write(`Command: ${backendCommand} ${launchArgs.join(" ")}\n`);
  backendLogStream.write(`OLLAMA_MODELS: ${backendEnv.OLLAMA_MODELS}\n`);
  backendLogStream.write(`OLLAMA_HOST: ${backendEnv.OLLAMA_HOST}\n`);
  backendLogStream.write(`Bundled model store copied: ${copiedBundledModels ? "yes" : "no"}\n`);
  if (bundledJavaHome) {
    backendLogStream.write(`JAVA_HOME: ${bundledJavaHome}\n`);
  }

  backendProcess = spawn(
    backendCommand,
    launchArgs,
    {
      cwd: launchCwd,
      env: backendEnv,
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
    }
  );

  backendProcess.stdout.on("data", (chunk) => backendLogStream.write(chunk));
  backendProcess.stderr.on("data", (chunk) => backendLogStream.write(chunk));
  backendProcess.once("exit", (code, signal) => {
    backendLogStream?.write(`[${new Date().toISOString()}] Backend exited code=${code} signal=${signal}\n`);
  });

  await waitForHealth(backendPort);
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1000,
    minHeight: 720,
    title: "HITL Academic Writing Scorer",
    backgroundColor: "#f5f7fb",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, "preload.cjs"),
      sandbox: false,
    },
  });

  const localOrigin = `http://${DEFAULT_HOST}:${backendPort}`;
  mainWindow.loadURL(`${localOrigin}/`);

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith(localOrigin)) {
      return { action: "allow" };
    }
    shell.openExternal(url);
    return { action: "deny" };
  });

  mainWindow.webContents.on("will-navigate", (event, url) => {
    if (!url.startsWith(localOrigin)) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });
}

function stopBackend() {
  if (!backendProcess || backendProcess.killed) {
    backendLogStream?.end();
    return;
  }

  if (backendPort) {
    const request = http.request({
      host: DEFAULT_HOST,
      port: backendPort,
      path: "/shutdown",
      method: "POST",
      timeout: 1000,
    });
    request.on("error", () => {});
    request.end();
  }

  setTimeout(() => {
    if (backendProcess && !backendProcess.killed) {
      backendProcess.kill();
    }
    backendLogStream?.end();
  }, 1500).unref();
}

app.whenReady().then(async () => {
  try {
    await startBackend();
    createWindow();
  } catch (error) {
    dialog.showErrorBox(
      "HITL failed to start",
      `${error.message}\n\nCheck that Python and the HITL dependencies are installed for this development build.`
    );
    app.quit();
  }
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0 && backendPort) {
    createWindow();
  }
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  stopBackend();
});
